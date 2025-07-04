import argparse
import json
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import _helpers
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.base_document import DocumentSnapshot
import click


# Initialize Firebase Admin
def initialize_firestore(
    certificate_path: str | None = None,
) -> firestore.firestore.Client:
    cred = (
        credentials.Certificate(certificate_path)
        if certificate_path
        else credentials.ApplicationDefault()
    )
    firebase_admin.initialize_app(cred)
    return firestore.client()

class OptionalFirestoreEncoder(json.JSONEncoder):
    """ Invoked by json.dump() or json.dumps() to decode and dereference Firestore objects.
        Handles special data types that can't be directly encoded in JSON.

        Currently handles the following types:
        - DocumentReference:
            - is_recursive=False: Return a string with path to the reference
            - is_recursive=True:  Fetch the referenced document if possible. Return the
              dictionary version of the object. Some of the members of the dictionary will
              be DocumentSnapshot objects, which we handle.
        - DocumentSnapshot: Return the ToDictionary() version of it
        - DatetimeWithNanoseconds: Return a string with the RFC 3339 version of the time
            e.g.: "2025-03-31T00:00:00.000000Z"
    """
    recursive = False

    def default(self, obj):
        if isinstance(obj, DocumentSnapshot):
            """
                If the object is a document snapshot, return its dictionary form
            """
            retval = obj.to_dict()
            return retval

        if isinstance(obj, DocumentReference):
            """
                If the object is a document reference, we either turn the reference
                path into a string (is_recusive=False) or we fetch the referenced
                document and add it as a dictionary element of the current document.
            """
            if OptionalFirestoreEncoder.recursive:
                doc = obj.get()
                if doc.exists:
                    return doc.to_dict()
                else:
                    return f"ERROR: ref to {obj.path} but fetching that document failed"
            else:
                return f"ref: {obj.path}"
        if isinstance(obj, _helpers.DatetimeWithNanoseconds):
            """
                Firebase sometimes uses this weird datetime that has nanoseconds, not milliseconds.
                It can't be serialised by the default encoder. Turn it into an rfc3339() datetime
            """
            return obj.rfc3339()
        return super().default(obj)


# Parse command line arguments
@click.command()
@click.option(
    "--credentials",
    required=False,
    help="Path to Firebase credentials JSON",
    default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
)
@click.option("--path", required=True, help="Path to Firestore collection")
@click.option("--group", is_flag=True, help="whether this is a group query")
@click.option(
    "--where",
    multiple=True,
    required=False,
    help="Query in the format 'field operation value' (e.g. name == Alice)",
)
@click.option(
    "--id",
    required=False,
    help="Query for a specific document ID",
)
@click.option(
    "--orderby",
    multiple=True,
    required=False,
    help="Field to order by, followed by ASCENDING or DESCENDING",
)
@click.option("--recursive", type=bool, is_flag=True, required=False,
              help="Follow references to return the document they reference"
)
@click.option("--limit", type=int, help="Limit the number of results")
def main(credentials, path, group, where, id, orderby, limit, recursive):
    db = initialize_firestore(credentials)
    results = execute_query(db, path, group, id, where, orderby, limit)
    OptionalFirestoreEncoder.recursive = recursive
    print(json.dumps(results, indent=2, ensure_ascii=False, cls=OptionalFirestoreEncoder))


def convert_string(input_str):
    # Check if the string starts with 'int:', 'bool:', or 'float:' and convert accordingly
    if input_str.startswith("int:"):
        return int(input_str[4:])
    elif input_str.startswith("bool:"):
        # Convert the string following 'bool:' to a boolean
        # 'True' and 'False' are the typical string representations
        return input_str[5:].lower() == "true"
    elif input_str.startswith("float:"):
        return float(input_str[6:])
    else:
        # Return the original string if it doesn't match any of the specified prefixes
        return input_str


# Execute query and return results
def execute_query(
    db: firestore.firestore.Client,
    collection_path: str,
    is_group: bool,
    id,
    query,
    orderby,
    limit,
):
    if is_group:
        collection = db.collection_group(collection_path)
    else:
        collection = db.collection(collection_path)
    query_result = collection
    if id is not None:
        # Simple query for document by id
        query_result = query_result.document(id)  # type: ignore
        doc = query_result.get()
        return doc.to_dict() if doc.exists else None
    elif query is not None:
        for subquery in query:
            field, operation, value = subquery.split(" ")
            # print(field, operation, value)
            value = convert_string(value)
            filter = FieldFilter(field, operation, value)
            query_result = query_result.where(filter=filter)
    if orderby is not None:
        for field in orderby:
            field, order = field.split(" ")
            query_result = query_result.order_by(field, order)  # type: ignore
    if limit:
        query_result = query_result.limit(limit)

    return [doc.to_dict() for doc in query_result.stream()]


if __name__ == "__main__":
    main()
