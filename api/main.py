import falcon
import config
import mainhandler
import symbolhandler

configFile = config.findConfigFile(
    [ '../config/pysymproxy.json'
    , './config/pysymproxy.json'
    , './config/default.pysymproxy.json'])

configuration = config.Config(configFile)

symhandler = symbolhandler.SymbolHandler(configuration)

api = falcon.API()
api.add_route('/{file}', mainhandler.MainHandler(configuration, symhandler.getStats()))
api.add_route('/symbols/{file}/{identifier}/{rawfile}', symhandler)
