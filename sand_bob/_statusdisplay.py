class StatusDisplay:
    def __init__(self, status_text: str = "Starting..."):
        # detect if we are in a notebook
        from ._utilities import we_are_in_a_notebook
        if we_are_in_a_notebook():
            from IPython.display import display, DisplayHandle, HTML
            self.widget = DisplayHandle()
            self.widget.display(HTML(status_text))
        else:
            self.widget = None

    def update(self, status_text: str = "Processing..."):
        if self.widget is not None:
            from IPython.display import display, DisplayHandle, HTML
            self.widget.update(HTML(status_text))
