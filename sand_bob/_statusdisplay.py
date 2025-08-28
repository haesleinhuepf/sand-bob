class StatusDisplay:
    def __init__(self, total_steps: int = 100, status_text: str = "Starting..."):
        # detect if we are in a notebook
        from ._utilities import we_are_in_a_notebook
        if we_are_in_a_notebook():
            from IPython.display import display, DisplayHandle, HTML
            self.widget = DisplayHandle()
            self.widget.display(HTML(self._create_status_html(status_text, 0)))
        else:
            self.widget = None
        
        self.total_steps = total_steps
        self.current_steps = 0
        self.status_text = status_text

    def _create_status_html(self, status_text: str, percentage: float) -> str:
        """Create HTML for status display with progress bar"""
        # Ensure percentage is between 0 and 100
        percentage = max(0, min(100, percentage))
        
        # Create slim progress bar with text overlay
        progress_bar_html = f"""
        <div style="position: relative; width: 100%; height: 20px; background-color: #f5f5f5; border-radius: 1px; margin: 0px 0px; overflow: hidden;">
        """

        if percentage > 0:
            progress_bar_html += f"""
            <div style="position: absolute; top: 0; left: 0; width: {percentage}%; height: 100%; background-color: #3874CC; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 0; left: 0; width: {percentage}%; height: 100%; display: flex; align-items: left; justify-content: left; z-index: 3;">
                <span style="color: #ffffff; font-size: 12px;">{status_text}</span>
            </div>
            """

        progress_bar_html += f"""
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: left; justify-content: left; z-index: 1;">
                <span style="color: #000000; font-size: 12px; position: relative; z-index: 2;">{status_text}</span>
            </div>
        </div>
        """
        
        return f"""
        <div style="font-family: Arial, sans-serif; padding: 0px;">
            {progress_bar_html}
        </div>
        """

    def add_progress(self, steps: int = 1):
        """Add progress by the specified number of steps"""
        self.current_steps += steps
        # Ensure we don't exceed total steps
        self.current_steps = min(self.current_steps, self.total_steps)
        self._update_display()


    def _update_display(self):
        """Update the display with current progress"""
        if self.widget is not None:
            from IPython.display import display, DisplayHandle, HTML
            
            # Calculate percentage based on current steps vs total steps
            percentage = (self.current_steps / self.total_steps) * 100 if self.total_steps > 0 else 0
            
            if self.status_text == "":
                self.widget.update(HTML(""))
            else:
                self.widget.update(HTML(self._create_status_html(self.status_text, percentage)))

    def update(self, status_text: str = "Processing..."):
        """Update status text and optionally set percentage directly (for backward compatibility)"""
        if status_text != "Processing...": 
            self.status_text = status_text
        
        self._update_display()
