"""
Example of a custom processor extending ProcessorModel.

This file demonstrates how users can create their own health-check
processors by inheriting from ProcessorModel and overriding the
success / failure hooks.
"""

from processor import ProcessorModel


class ExampleProcessor(ProcessorModel):
    """
    A custom processor that logs extra information on success
    and sends an alert on failure.
    """

    def success_send_request(self, send_request: float, get_response: float, duration: float):
        """
        Called after a successful HTTP request.
        Override this method to add custom behaviour (e.g., metrics, notifications).
        """
        # Call the parent implementation if needed (currently it does nothing)
        super().success_send_request(send_request, get_response, duration)

        # Your custom logic here
        print(f"[SUCCESS] {self.url} responded in {duration:.2f} s")

    def fail_send_request(self, send_request: float, get_response: float, exception: Exception):
        """
        Called when the HTTP request fails.
        Override this method to implement alerting or fallback logic.
        """
        # Call the parent implementation if needed
        super().fail_send_request(send_request, get_response, exception)

        # Your custom logic here (e.g., send an alert)
        print(f"[FAILURE] {self.url} failed with {type(exception).__name__}: {exception}")

    @classmethod
    def test_load(cls):
        """
        Optional: called by the server during startup to verify the processor loads.
        """
        print(f"Custom processor {cls.__qualname__} loaded successfully.")