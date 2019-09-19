#!/usr/bin/env python
from flask import Flask, request
from flask_restplus import Api, Resource, fields, abort
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
        content = {'hello': 'world'}
        headers = dict(request.headers)
        # Content-Length contained multiple unmatching values #15
        headers.pop('Content-Length', None)
        headers.pop('content-length', None)
        headers['X-FAKE-DATA'] = f'GET request on /test/{path}'
        return {**content, **headers}, 200, headers

    def post(self, path):
        content = request.get_json(force=True, silent=False)
        headers = dict(request.headers)
        # Content-Length contained multiple unmatching values #15
        headers.pop('Content-Length', None)
        headers.pop('content-length', None)
        headers['X-FAKE-DATA'] = f'POST request on /test/{path}'
        return {**content, **headers}, 201, headers

    def put(self, path):
        content = request.get_json(force=True, silent=False)
        headers = dict(request.headers)
        # Content-Length contained multiple unmatching values #15
        headers.pop('Content-Length', None)
        headers.pop('content-length', None)
        headers['X-FAKE-DATA'] = f'PUT request on {path}'
        return {**content, **headers}, 202, headers

    def delete(self, path):
        headers = dict(request.headers)
        # Content-Length contained multiple unmatching values #15
        headers.pop('Content-Length', None)
        headers.pop('content-length', None)
        headers['X-FAKE-DATA'] = f'DELETE request on /test/{path}'
        return {**content, **headers}, 201, headers



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
    logger.info("Starting the REST APi...")
    app.run(debug=debug, host=host, port=port)

if __name__ == '__main__':
    main()