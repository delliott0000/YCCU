from discord.ui import View, Button


class BanAppealView(View):

    def __init__(self, appeal_url: str, /) -> None:
        super().__init__(timeout=0)
        self.add_item(Button(label='Appeal Ban', url=appeal_url))
