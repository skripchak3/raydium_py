from time import sleep


class BeeperMixin:
    def bought_beeper(self):
        if self.beep:
            print("\a")
            print("\a")

    def sold_beeper(self):
        if self.beep:
            print("\a")
            sleep(0.12)
            print("\a")
