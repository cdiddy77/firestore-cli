import os
import click
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


# Initialize Firebase Admin
def initialize_firestore(certificate_path: str | None = None):
    cred = (
        credentials.Certificate(certificate_path)
        if certificate_path
        else credentials.ApplicationDefault()
    )
    firebase_admin.initialize_app(cred)
    return firestore.client()


def read_json_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def execute_update(db: firestore.firestore.Client, args):
    collection = db.collection(args["path"])
    # read the document from file path at args["doc"]
    if args["doc"]:
        doc = read_json_file(args["doc"])
    if args["set"]:
        return collection.document(args["set"]).set(doc)
    elif args["add"]:
        return collection.add(doc)[1].path.split("/")[-1]
    elif args["update"]:
        return collection.document(args["update"]).update(doc)
    elif args["delete"]:
        return collection.document(args["delete"]).delete()


@click.command()
@click.option(
    "--credentials",
    required=False,
    help="Path to Firebase credentials JSON",
    default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
)
@click.option("--path", required=True, help="Path to Firestore collection")
@click.option("--set", help="Set a document")
@click.option("--add", is_flag=True, help="Add a document")
@click.option("--update", help="Update a document")
@click.option("--delete", help="Delete a document")
@click.option("--doc", help="Path to document")
def main(path, set, add, update, delete, doc):
    args = {
        "path": path,
        "set": set,
        "add": add,
        "update": update,
        "delete": delete,
        "doc": doc,
    }
    db = initialize_firestore()
    results = execute_update(db, args)
    print(results)


if __name__ == "__main__":
    main()
