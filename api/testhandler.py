import os
import logging

logger = logging.getLogger(__name__)

class TestHandler:
    def __init__(self):
        pass

    def on_get(self, req, resp, file1, file2, file3):
        file_location = "./test/" + file1 + "/" + file2 + "/" + file3
        logging.info("get: {} client: {}".format(file_location, req.remote_addr))
        try:
            resp.stream = open(file_location, 'rb')
            resp.stream_len = os.path.getsize(file_location)
            resp.content_type = "application/octet-stream"

        except Exception, e:
            resp.body = "error: " + str(e)
