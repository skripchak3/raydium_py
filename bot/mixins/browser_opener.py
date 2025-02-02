import webbrowser


class BrowserOpenerMixin:
    def open_browser(self, pair_address: str):
        self.browser and webbrowser.open(
            f"https://photon-sol.tinyastro.io/en/lp/{pair_address}"
        )
