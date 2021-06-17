from MicroWebSrv2 import MicroWebSrv2, WebRoute, GET, POST


class WebServer:
    def __init__(self, metrics_callback, wdt):
        self.srv = MicroWebSrv2()
        self.srv.SetEmbeddedConfig()

        self.srv.metrics_callback = metrics_callback
        self.srv.wdt = wdt

    def start(self):
        self.srv.StartManaged()

    def stop(self):
        self.srv.Stop()

    @WebRoute(GET, "/")
    def RequestIndex(server, request):
        # Let watchdog know we are still receiving requests
        server.wdt.feed()

        return request.Response.ReturnOkJSON(
            {
                "ClientAddr": request.UserAddress,
                "Accept": request.Accept,
                "UserAgent": request.UserAgent,
            }
        )

    @WebRoute(POST, "/metrics")
    def PostMetrics(server, request):
        # Let watchdog know we are still receiving requests
        server.wdt.feed()

        server.metrics_callback(request.GetPostedJSONObject())
        return request.Response.ReturnOkJSON({})
