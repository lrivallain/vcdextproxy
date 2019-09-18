#!/usr/bin/env python
from flask import Flask, request
from flask_restplus import Api, Resource, fields, abort
from .utils import configure_logger
import logging
import click


logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
app.config['SWAGGER_UI_OPERATION_ID'] = True
app.config['SWAGGER_UI_REQUEST_DURATION'] = True
app.config['RESTPLUS_MASK_SWAGGER'] = False
api = Api(
    app,
    version='1.0',
    title='Fake REST API server for vCD extension',
    description='This REST API returns the initial content of the request as a response.',
)


@api.route('/test/<string:path>')
class RootApi(Resource):
    def get(self, path):
        logger.info(f"GET request")
        h = dict(request.headers)
        h['X-FAKE-DATA'] = f'GET request on /test/{path}'
        return {'hello': 'world'}, 200, h

    def post(self, path):
        logger.info(f"POST request")
        content = request.get_json(force=True, silent=False)
        headers = dict(request.headers)
        headers['X-FAKE-DATA'] = f'POST request on /test/{path}'
        return content, 201, headers

    def put(self, path):
        logger.info(f"PUT request")
        content = request.get_json(force=True, silent=False)
        headers = dict(request.headers)
        headers['X-FAKE-DATA'] = f'PUT request on {path}'
        return content, 202, headers

    def delete(self, path):
        logger.info(f"DELETE request")
        headers = dict(request.headers)
        headers['X-FAKE-DATA'] = f'DELETE request on /test/{path}'
        return {}, 202, headers



@click.command()
@click.option('-h', '--host', default="127.0.0.1",
    help="Bind server to a specific interface"
)
@click.option('-p', '--port', default="5000",
    help='Bind server to a specific port'
)
@click.option('-v', '--debug', is_flag=True,
    help="Enable Flask debug mode"
)
def main(host, port, debug):
    """Execute the REST APi.
    """
    configure_logger()
    logger.info("Starting the REST APi...")
    app.run(debug=debug, host=host, port=port)

if __name__ == '__main__':
    main()