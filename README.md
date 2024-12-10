# Firestore CLI

This CLI tool allows you to interact with Google Firestore using command-line commands. It includes two main scripts: `fsquery` and `fsupdate`.

## Installation

1. Install from PyPI:

   ```sh
   pip install firestore-cli
   ```

## Usage

### Credentials

"""
This script allows querying a Firestore database using various command-line options.

To specify the credentials necessary to access Firestore, you can use either of the following methods:

1. Using the `--credentials` option:

   - Provide the path to the Firebase credentials JSON file directly via the `--credentials` command-line option.
   - Example usage:
     ```
     fsquery --credentials /path/to/your/credentials.json --path your/firestore/collection
     ```

2. Using the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:
   - Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your Firebase credentials JSON file.
   - Example usage:
     ```
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
     fsquery --path your/firestore/collection
     ```

If neither method is provided, the script will attempt to use the default application credentials.
"""

### fsupdate

The `fsupdate` script allows you to set, add, update, or delete documents in a Firestore collection.

#### Command Line Options

- `--path`: Path to the Firestore collection (required).
- `--set`: Set a document with the specified ID.
- `--add`: Add a new document.
- `--update`: Update a document with the specified ID.
- `--delete`: Delete a document with the specified ID.
- `--doc`: Path to the JSON file containing the document data.

#### Examples

1. **Set a document**:

   ```sh
   fsupdate --path your-collection --set your-document-id --doc path/to/your/document.json
   ```

2. **Add a document**:

   ```sh
   fsupdate --path your-collection --add --doc path/to/your/document.json
   ```

3. **Update a document**:

   ```sh
   fsupdate --path your-collection --update your-document-id --doc path/to/your/document.json
   ```

4. **Delete a document**:
   ```sh
   fsupdate --path your-collection --delete your-document-id
   ```

### fsquery

The `fsquery` script allows you to query documents from a Firestore collection.

#### Command Line Options

- `--path`: Path to the Firestore collection (required).
- `--group`: Specify if this is a collection group query (optional).
- `--where`: Apply multiple filters to the query in the format `field:operation:value` e.g. `--where "some_field == some_value"` (optional). It is recommended to place quotes around the expression.
- `--id`: Query for a specific document ID (optional).
- `--orderby`: Order the results by specified fields, followed by `ASCENDING` or `DESCENDING` (optional).
- `--limit`: Limit the number of results (optional).

#### Examples

1. **Query all documents in a collection**:

   ```sh
   fsquery --path your-collection
   ```

2. **Query documents with a filter**:

   ```sh
   fsquery --path your-collection --where "field_name == value"
   ```

## License

This project is licensed under the MIT License.
