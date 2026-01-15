"""
File storage endpoints for NFS operations.

Provides endpoints for listing, reading, writing, and deleting
files within the configured data directory.
"""

import logging

from flask import Blueprint, current_app, jsonify, request
from opentelemetry import trace

from app.services.storage import (
    DirectoryNotEmptyError,
    InvalidPathError,
    PathNotFoundError,
    StorageService,
    get_storage_service,
    init_storage_service,
)

files_bp = Blueprint("files", __name__, url_prefix="/files")
logger = logging.getLogger(__name__)


def get_tracer() -> trace.Tracer:
    """Get the tracer from the current app context."""
    return current_app.config.get("TRACER") or trace.get_tracer(__name__)


def _get_or_init_storage_service() -> StorageService:
    """Get storage service, initializing if needed."""
    try:
        return get_storage_service()
    except RuntimeError:
        config = current_app.config.get("APP_CONFIG")
        if config:
            return init_storage_service(config)
        raise


@files_bp.route("", methods=["GET"])
@files_bp.route("/", methods=["GET"])
@files_bp.route("/<path:filepath>", methods=["GET"])
def get_files(filepath: str = ""):
    """List files or read file content.
    ---
    tags:
      - Files
    summary: List directory or read file
    description: |
      If path is a directory, returns a list of files and subdirectories.
      If path is a file, returns the file content.
      Supports nested paths like `/files/subdir/file.txt`.
    parameters:
      - name: filepath
        in: path
        type: string
        required: false
        description: Path to file or directory (relative to storage root)
        default: ""
    responses:
      200:
        description: Directory listing or file content
        schema:
          type: object
          properties:
            path:
              type: string
              example: "subdir"
            type:
              type: string
              enum: [directory, file]
              example: directory
            items:
              type: array
              description: Only present for directories
              items:
                type: object
                properties:
                  name:
                    type: string
                  type:
                    type: string
                    enum: [file, directory]
                  size:
                    type: integer
            content:
              type: string
              description: Only present for files
            size:
              type: integer
              description: File size in bytes (only for files)
            trace_id:
              type: string
      404:
        description: Path not found
      400:
        description: Invalid path (path traversal attempt)
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("files-get") as span:
        span.set_attribute("file.path", filepath or "/")

        try:
            storage = _get_or_init_storage_service()
            trace_id = format(span.get_span_context().trace_id, "032x")

            if storage.is_directory(filepath):
                span.set_attribute("file.type", "directory")
                items = storage.list_directory(filepath)
                span.set_attribute("file.item_count", len(items))

                return jsonify(
                    {
                        "path": filepath or "/",
                        "type": "directory",
                        "items": [item.to_dict() for item in items],
                        "trace_id": trace_id,
                    }
                )
            else:
                span.set_attribute("file.type", "file")
                content, size = storage.read_file(filepath)
                span.set_attribute("file.size", size)

                return jsonify(
                    {
                        "path": filepath,
                        "type": "file",
                        "content": content,
                        "size": size,
                        "trace_id": trace_id,
                    }
                )

        except InvalidPathError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": filepath}), 400

        except PathNotFoundError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Not found"))
            return jsonify({"error": "Path not found", "path": filepath}), 404


@files_bp.route("/<path:filepath>", methods=["POST", "PUT"])
def write_file(filepath: str):
    """Write content to a file.
    ---
    tags:
      - Files
    summary: Create or update a file
    description: |
      Writes content to a file. Creates parent directories if they don't exist.
      Content should be sent as the request body (text/plain or application/json with "content" field).
    parameters:
      - name: filepath
        in: path
        type: string
        required: true
        description: Path to the file (relative to storage root)
      - name: body
        in: body
        required: true
        description: File content (plain text or JSON with "content" field)
        schema:
          type: object
          properties:
            content:
              type: string
              example: "Hello, World!"
    responses:
      201:
        description: File created
        schema:
          type: object
          properties:
            status:
              type: string
              example: created
            path:
              type: string
            size:
              type: integer
            trace_id:
              type: string
      200:
        description: File updated
        schema:
          type: object
          properties:
            status:
              type: string
              example: updated
            path:
              type: string
            size:
              type: integer
            trace_id:
              type: string
      400:
        description: Invalid path or missing content
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("files-write") as span:
        span.set_attribute("file.path", filepath)

        try:
            storage = _get_or_init_storage_service()

            # Get content from request
            if request.is_json:
                data = request.get_json()
                content = data.get("content", "")
            else:
                content = request.get_data(as_text=True)

            if content is None:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "No content"))
                return jsonify({"error": "No content provided"}), 400

            status, size = storage.write_file(filepath, content)
            span.set_attribute("file.size", size)
            span.set_attribute("file.created", status == "created")

            status_code = 201 if status == "created" else 200

            return jsonify(
                {
                    "status": status,
                    "path": filepath,
                    "size": size,
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            ), status_code

        except InvalidPathError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": filepath}), 400


@files_bp.route("/<path:filepath>", methods=["DELETE"])
def delete_file(filepath: str):
    """Delete a file or empty directory.
    ---
    tags:
      - Files
    summary: Delete a file or empty directory
    description: |
      Deletes a file or an empty directory.
      Non-empty directories cannot be deleted (returns 400).
    parameters:
      - name: filepath
        in: path
        type: string
        required: true
        description: Path to the file or directory to delete
    responses:
      200:
        description: File or directory deleted
        schema:
          type: object
          properties:
            status:
              type: string
              example: deleted
            path:
              type: string
            type:
              type: string
              enum: [file, directory]
            trace_id:
              type: string
      404:
        description: Path not found
      400:
        description: Invalid path or directory not empty
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("files-delete") as span:
        span.set_attribute("file.path", filepath)

        try:
            storage = _get_or_init_storage_service()
            file_type = storage.delete(filepath)
            span.set_attribute("file.type", file_type)

            return jsonify(
                {
                    "status": "deleted",
                    "path": filepath,
                    "type": file_type,
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }
            )

        except InvalidPathError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": "Invalid path", "path": filepath}), 400

        except PathNotFoundError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Not found"))
            return jsonify({"error": "Path not found", "path": filepath}), 404

        except DirectoryNotEmptyError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Not empty"))
            return jsonify({"error": "Directory not empty", "path": filepath}), 400


@files_bp.route("", methods=["POST"])
def create_directory():
    """Create a new directory.
    ---
    tags:
      - Files
    summary: Create a directory
    description: Creates a new directory. Parent directories are created if needed.
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - path
          properties:
            path:
              type: string
              description: Directory path to create
              example: "subdir/newdir"
    responses:
      201:
        description: Directory created
        schema:
          type: object
          properties:
            status:
              type: string
              example: created
            path:
              type: string
            type:
              type: string
              example: directory
            trace_id:
              type: string
      200:
        description: Directory already exists
      400:
        description: Invalid path or missing path parameter
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("files-mkdir") as span:
        if not request.is_json:
            return jsonify({"error": "JSON body required"}), 400

        data = request.get_json()
        dirpath = data.get("path", "")

        if not dirpath:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "No path"))
            return jsonify({"error": "Path is required"}), 400

        span.set_attribute("file.path", dirpath)

        try:
            storage = _get_or_init_storage_service()
            status = storage.create_directory(dirpath)
            trace_id = format(span.get_span_context().trace_id, "032x")

            status_code = 201 if status == "created" else 200

            return jsonify(
                {
                    "status": status,
                    "path": dirpath,
                    "type": "directory",
                    "trace_id": trace_id,
                }
            ), status_code

        except InvalidPathError as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid path"))
            return jsonify({"error": str(e), "path": dirpath}), 400
