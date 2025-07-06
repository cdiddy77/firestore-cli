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


class FirestoreEncoder(json.JSONEncoder):
    """ Invoked by json.dump() or json.dumps() to decode and dereference Firestore objects.
        Handles special data types that can't be directly encoded in JSON.

        Currently handles the following types:
        - DocumentReference: Check the current value of recursion (default: 0)
            - <= 0: We are at the limits of allowed recursion: Return a string with path to the reference
            - > 0:  We are not yet at the limits of allowed recursion: Fetch the referenced document if
              possible. Return the dictionary version of the object. Some of the members of the dictionary
              will be DocumentSnapshot objects, which we also handle.
        - DocumentSnapshot: Return the ToDictionary() version of it
        - DatetimeWithNanoseconds: Return a string with the RFC 3339 version of the time
            e.g.: "2025-03-31T00:00:00.000000Z"
    """
    recursion = 0

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

                There's a bit of janky loop-breaking here. It's possible to have circular
                references: doca.owner = ref: users/person1 and then person1.defaultdoc = ref: docs/doca

                This attempts to prevent dereferencing them infinitely. But it doesn't quite work right.
            """
            if FirestoreEncoder.recursion:
                if self.recursion > 0:
                    self.recursion -= 1
                    doc = obj.get()
                    if doc.exists:
                        return doc.to_dict()
                    else:
                        return f"ERROR: ref to {obj.path} but fetching that document failed"
                else:
                    # We have already dereferenced as much as we should. Return a simple string.
                    return f"xref: {obj.path}"
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
@click.command(context_settings={"show_default": True}, no_args_is_help=True)
@click.option("--path", required=True, help="Path to Firestore collection")
@click.option(
    "--credentials",
    required=False, show_default=True,
    help="Path to Firebase credentials JSON",
    default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
)
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
@click.option(
    "--out", required=False,
    help="Name of a file to write to, instead of stdout",
)
@click.option("--recursion", default=0, show_default=True,
              type=int, required=False,
              help="Follow references to a depth of X, including the document they reference in the output. Depth 0 means do not follow any references."
)
@click.option("--limit", type=int, help="Return no more than X results")
def main(credentials, path, group, where, id, orderby, limit, recursion, out):
    """ fsquery - Query firestore collections interactively from the command line.

        Automatically converts times to RFC 3339 format, and optionally dereferences
        any referenced documents to return a complete document.
    """
    db = initialize_firestore(credentials)
    results = execute_query(db, path, group, id, where, orderby, limit)
    FirestoreEncoder.recursion = recursion
    output = json.dumps(results, indent=2, ensure_ascii=False, cls=FirestoreEncoder)
    if out:
        try:
            with open(out, "w") as f:
                f.write(output)
        except Exception as e:
            print(e)
    else:
        print(output)


def convert_string(input_str) -> int|str|float:
    """
        Check if the string starts with 'int:', 'bool:', or 'float:' and convert accordingly
    """
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
