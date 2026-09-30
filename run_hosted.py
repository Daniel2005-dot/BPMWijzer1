"""Start the hosted WSGI app with Waitress."""
import os

from waitress import serve

from wsgi import application


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    serve(application, host=host, port=port)
