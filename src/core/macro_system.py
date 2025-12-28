"""
Macro Recording and Replay System.

Provides input automation capabilities for recording and replaying
keyboard and mouse sequences, useful for automating page turns
in manga readers after OCR capture.
"""

from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Callable, Any
import json


class EventType(Enum):
    """Types of input events."""
    KEY_DOWN = auto()
    KEY_UP = auto()
    MOUSE_CLICK = auto()
    MOUSE_DOWN = auto()
    MOUSE_UP = auto()
    MOUSE_MOVE = auto()
    MOUSE_SCROLL = auto()


@dataclass
class InputEvent:
    """Represents a single input event."""
    event_type: EventType
    timestamp: float  # Relative to recording start
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.name,
            "timestamp": self.timestamp,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, d: dict) -> InputEvent:
        """Create from dictionary."""
        return cls(
            event_type=EventType[d["event_type"]],
            timestamp=d["timestamp"],
            data=d.get("data", {})
        )


class MacroState(Enum):
    """State of the macro system."""
    IDLE = auto()
    RECORDING = auto()
    PLAYING = auto()


class MacroManager:
    """
    Manages macro recording and playback.

    Uses the keyboard and mouse libraries for global input
    hooking and event replay.
    """

    def __init__(self) -> None:
        """Initialize the macro manager."""
        self._state = MacroState.IDLE
        self._events: List[InputEvent] = []
        self._start_time: float = 0.0
        self._kill_key: str = "f12"
        self._kill_requested = False

        # Callbacks
        self._on_recording_complete: Optional[Callable[[List[InputEvent]], None]] = None
        self._on_playback_complete: Optional[Callable[[], None]] = None
        self._on_state_change: Optional[Callable[[MacroState], None]] = None

        # Thread for playback
        self._playback_thread: Optional[threading.Thread] = None

        # Check for available libraries
        self._keyboard_available = False
        self._mouse_available = False
        self._check_libraries()

    def _check_libraries(self) -> None:
        """Check which input libraries are available."""
        try:
            import keyboard
            self._keyboard_available = True
        except (ImportError, OSError) as e:
            print(f"Warning: keyboard library not available: {e}")

        try:
            import mouse
            self._mouse_available = True
        except (ImportError, OSError) as e:
            print(f"Warning: mouse library not available: {e}")

    @property
    def state(self) -> MacroState:
        """Get current macro state."""
        return self._state

    @property
    def events(self) -> List[InputEvent]:
        """Get recorded events."""
        return self._events.copy()

    @property
    def is_available(self) -> bool:
        """Check if macro system is available."""
        return self._keyboard_available or self._mouse_available

    def set_kill_key(self, key: str) -> None:
        """Set the key that stops playback."""
        self._kill_key = key

    def set_callbacks(
        self,
        on_recording_complete: Optional[Callable[[List[InputEvent]], None]] = None,
        on_playback_complete: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[MacroState], None]] = None
    ) -> None:
        """Set callback functions."""
        self._on_recording_complete = on_recording_complete
        self._on_playback_complete = on_playback_complete
        self._on_state_change = on_state_change

    def _set_state(self, state: MacroState) -> None:
        """Update state and notify callback."""
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def start_recording(self) -> bool:
        """
        Start recording input events.

        Returns:
            True if recording started successfully
        """
        if self._state != MacroState.IDLE:
            print("Cannot start recording: not in idle state")
            return False

        if not self.is_available:
            print("Cannot start recording: no input libraries available")
            return False

        self._events.clear()
        self._start_time = time.time()
        self._set_state(MacroState.RECORDING)

        # Hook keyboard events
        if self._keyboard_available:
            try:
                import keyboard
                keyboard.hook(self._on_keyboard_event)
            except Exception as e:
                print(f"Failed to hook keyboard: {e}")

        # Hook mouse events
        if self._mouse_available:
            try:
                import mouse
                mouse.hook(self._on_mouse_event)
            except Exception as e:
                print(f"Failed to hook mouse: {e}")

        print("Recording started. Press kill key to stop.")
        return True

    def stop_recording(self) -> List[InputEvent]:
        """
        Stop recording and return captured events.

        Returns:
            List of recorded events
        """
        if self._state != MacroState.RECORDING:
            return self._events

        # Unhook events
        if self._keyboard_available:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                pass

        if self._mouse_available:
            try:
                import mouse
                mouse.unhook_all()
            except Exception:
                pass

        self._set_state(MacroState.IDLE)
        print(f"Recording stopped. {len(self._events)} events captured.")

        if self._on_recording_complete:
            self._on_recording_complete(self._events)

        return self._events

    def _on_keyboard_event(self, event) -> None:
        """Handle keyboard events during recording."""
        if self._state != MacroState.RECORDING:
            return

        # Check for kill key
        if event.name == self._kill_key and event.event_type == "down":
            self.stop_recording()
            return

        # Record event
        event_type = EventType.KEY_DOWN if event.event_type == "down" else EventType.KEY_UP
        timestamp = time.time() - self._start_time

        self._events.append(InputEvent(
            event_type=event_type,
            timestamp=timestamp,
            data={"key": event.name, "scan_code": event.scan_code}
        ))

    def _on_mouse_event(self, event) -> None:
        """Handle mouse events during recording."""
        if self._state != MacroState.RECORDING:
            return

        timestamp = time.time() - self._start_time

        # Determine event type
        event_name = type(event).__name__

        if event_name == "ButtonEvent":
            if event.event_type == "down":
                event_type = EventType.MOUSE_DOWN
            elif event.event_type == "up":
                event_type = EventType.MOUSE_UP
            else:
                event_type = EventType.MOUSE_CLICK

            self._events.append(InputEvent(
                event_type=event_type,
                timestamp=timestamp,
                data={"button": event.button, "x": event.x, "y": event.y}
            ))

        elif event_name == "MoveEvent":
            self._events.append(InputEvent(
                event_type=EventType.MOUSE_MOVE,
                timestamp=timestamp,
                data={"x": event.x, "y": event.y}
            ))

        elif event_name == "WheelEvent":
            self._events.append(InputEvent(
                event_type=EventType.MOUSE_SCROLL,
                timestamp=timestamp,
                data={"delta": event.delta}
            ))

    def play(self, events: Optional[List[InputEvent]] = None) -> bool:
        """
        Play back recorded events in a background thread.

        Args:
            events: Events to play (uses recorded events if None)

        Returns:
            True if playback started successfully
        """
        if self._state != MacroState.IDLE:
            print("Cannot play: not in idle state")
            return False

        events_to_play = events if events is not None else self._events
        if not events_to_play:
            print("No events to play")
            return False

        self._kill_requested = False
        self._set_state(MacroState.PLAYING)

        # Set up kill key listener
        if self._keyboard_available:
            try:
                import keyboard
                keyboard.on_press(self._on_kill_key, suppress=False)
            except Exception as e:
                print(f"Failed to set up kill key: {e}")

        # Start playback thread
        self._playback_thread = threading.Thread(
            target=self._playback_worker,
            args=(events_to_play,),
            daemon=True
        )
        self._playback_thread.start()

        return True

    def _on_kill_key(self, event) -> None:
        """Handle kill key press during playback."""
        if self._state == MacroState.PLAYING and event.name == self._kill_key:
            self._kill_requested = True
            print("Kill key pressed, stopping playback...")

    def _playback_worker(self, events: List[InputEvent]) -> None:
        """Worker thread for event playback."""
        try:
            import keyboard
            import mouse
        except ImportError:
            self._set_state(MacroState.IDLE)
            return

        print(f"Playing {len(events)} events...")
        prev_timestamp = 0.0

        for event in events:
            if self._kill_requested:
                print("Playback aborted")
                break

            # Wait for correct timing
            delay = event.timestamp - prev_timestamp
            if delay > 0:
                time.sleep(delay)
            prev_timestamp = event.timestamp

            if self._kill_requested:
                break

            # Execute event
            try:
                self._execute_event(event)
            except Exception as e:
                print(f"Error executing event: {e}")

        # Cleanup
        if self._keyboard_available:
            try:
                keyboard.unhook(self._on_kill_key)
            except Exception:
                pass

        self._set_state(MacroState.IDLE)
        print("Playback complete")

        if self._on_playback_complete:
            self._on_playback_complete()

    def _execute_event(self, event: InputEvent) -> None:
        """Execute a single input event."""
        import keyboard
        import mouse

        if event.event_type == EventType.KEY_DOWN:
            keyboard.press(event.data["key"])

        elif event.event_type == EventType.KEY_UP:
            keyboard.release(event.data["key"])

        elif event.event_type == EventType.MOUSE_DOWN:
            mouse.press(event.data.get("button", "left"))

        elif event.event_type == EventType.MOUSE_UP:
            mouse.release(event.data.get("button", "left"))

        elif event.event_type == EventType.MOUSE_CLICK:
            mouse.click(event.data.get("button", "left"))

        elif event.event_type == EventType.MOUSE_MOVE:
            mouse.move(event.data["x"], event.data["y"])

        elif event.event_type == EventType.MOUSE_SCROLL:
            mouse.wheel(event.data["delta"])

    def stop(self) -> None:
        """Stop any ongoing operation."""
        if self._state == MacroState.RECORDING:
            self.stop_recording()
        elif self._state == MacroState.PLAYING:
            self._kill_requested = True

    def load_events(self, events_data: List[dict]) -> None:
        """Load events from serialized format."""
        self._events = [InputEvent.from_dict(e) for e in events_data]

    def save_events(self) -> List[dict]:
        """Save events to serializable format."""
        return [e.to_dict() for e in self._events]

    def clear_events(self) -> None:
        """Clear recorded events."""
        self._events.clear()


# Global instance
_macro_manager: Optional[MacroManager] = None


def get_macro_manager() -> MacroManager:
    """Get the global macro manager instance."""
    global _macro_manager
    if _macro_manager is None:
        _macro_manager = MacroManager()
    return _macro_manager
