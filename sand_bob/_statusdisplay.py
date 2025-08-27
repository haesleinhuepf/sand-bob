class StatusDisplay:
    def __init__(self, status_text: str = "Starting..."):
        # detect if we are in a notebook
        from ._utilities import we_are_in_a_notebook
        if we_are_in_a_notebook():
            from IPython.display import display, DisplayHandle, HTML
            self.widget = DisplayHandle()
            self.widget.display(HTML(self._create_status_html(status_text, 0)))
        else:
            self.widget = None

    def _create_status_html(self, status_text: str, percentage: float) -> str:
        """Create HTML for status display with progress bar"""
        # Ensure percentage is between 0 and 100
        percentage = max(0, min(100, percentage))
        
        # Create slim progress bar with text overlay
        progress_bar_html = f"""
        <div style="position: relative; width: 100%; height: 20px; background-color: #f5f5f5; border-radius: 1px; margin: 0px 0px; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; width: {percentage}%; height: 100%; background-color: #3874CC; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: left; justify-content: center; z-index: 1;">
                <span style="color: #000000; font-size: 12px; position: relative; z-index: 2;">{status_text}</span>
            </div>
            <div style="position: absolute; top: 0; left: 0; width: {percentage}%; height: 100%; display: flex; align-items: left; justify-content: center; z-index: 3;">
                <span style="color: #ffffff; font-size: 12px;">{status_text}</span>
            </div>
        </div>
        """
        
        return f"""
        <div style="font-family: Arial, sans-serif; padding: 0px;">
            {progress_bar_html}
        </div>
        """

    def update(self, status_text: str = "Processing...", percentage: float = 0.0):
        if self.widget is not None:
            from IPython.display import display, DisplayHandle, HTML
            if status_text == "":
                self.widget.update(HTML(""))
            else:
                self.widget.update(HTML(self._create_status_html(status_text, percentage)))
