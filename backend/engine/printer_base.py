from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BasePrinterEngine(ABC):
    @abstractmethod
    def list_printers(self) -> List[Dict[str, Any]]:
        """List all available printers on the system."""
        pass

    @abstractmethod
    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Get detailed status, state, and ink/paper levels of a specific printer."""
        pass

    @abstractmethod
    def print_file(self, printer_name: str, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Send a print job to the specified printer with options."""
        pass

    @abstractmethod
    def get_jobs(self, printer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active and pending print jobs."""
        pass

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a print job by ID."""
        pass
