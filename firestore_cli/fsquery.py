import argparse
import json
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
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
@click.option("--limit", type=int, help="Limit the number of results")
def main(credentials, path, group, where, id, orderby, limit):
    db = initialize_firestore(credentials)
    results = execute_query(db, path, group, id, where, orderby, limit)
    print(json.dumps(results, indent=2))


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
