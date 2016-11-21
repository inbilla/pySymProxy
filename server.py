from api.main import api
from waitress import serve
import logging

logger = logging.getLogger(__name__)
logger.info("Starting SymProxy Server")
print "Test link: http://localhost:8080/symbols/wntdll.pdb/F999943DF7FB4B8EB6D99F2B047BC3101/wntdll.pdb"
serve(api, host='0.0.0.0', port=8080)

#TODO:
# - Add lazy evaluation of storage space
# - Avoid timeouts somehow on requests that run for a long time
# - Detect when entire servers are down and stop attempting to fetch from them for a while
# - Add cache budget management