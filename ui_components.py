# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista — shared UI components (v1.7), from notes/notes_006.txt §4.

Four self-contained CustomTkinter building blocks: a focusable action
button, a floating hover HUD, a bounded toast notification manager, and a
tag chip selector. They import no Desktop Vista engine code and cannot set
a wallpaper or write config — desktop_vista.py wires their callbacks to
the real handlers and owns all persistence. All widget methods run on
Tk's owning thread; ToastManager.post() alone is safe to call from a
worker thread (it only pushes onto a bounded queue).

Blueprint limits that remain true here: no complete screen-reader
provider or multi-select bulk editor for tags; the toast manager doesn't
replace decision dialogs (messagebox stays for those); the HUD has no
per-child alpha (CustomTkinter's "transparent" paints the parent colour,
not per-widget translucency); all three depend on the caller's own
keyboard-shortcut guard to avoid double-handling typed characters.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import customtkinter as ctk

LOG = logging.getLogger("desktop_vista.ui")

# Design tokens (notes_006 §2.6) — light, dark.
SURFACE = ("#F7F7F7", "#2C2C2C")
TEXT = ("#1A1A1A", "#F5F5F5")
BORDER = ("#737373", "#949494")
FOCUS = ("#005FB8", "#75B6FF")
ERROR_TEXT = ("#A4262C", "#FFB4AB")


def contains_widget(parent: tk.Misc, child: Optional[tk.Misc]) -> bool:
    while child is not None:
        if child is parent:
            return True
        child = getattr(child, "master", None)
    return False


def pointer_inside(widget: tk.Misc) -> bool:
    if not widget.winfo_ismapped():
        return False
    x, y = widget.winfo_pointerxy()
    return contains_widget(widget, widget.winfo_containing(x, y))


class ActionButton(ctk.CTkButton):
    """A CTkButton that actually accepts keyboard focus. CTkButton 5.2.2
    delegates focus to an internal text label and exposes no working
    takefocus argument, so this puts focus on the native outer Frame via
    plain Tk APIs — never reaching into CTk's private canvas/entry
    internals. CTk's own mouse bindings are kept (additive `add="+"`).
    Keyboard activation returns "break" so it doesn't also propagate to a
    parent shortcut binding; call set_enabled() rather than configuring
    state directly so keyboard traversal stays consistent with visibility.
    """

    def __init__(self, master, *, text: str, command: Callable[[], None], width: int = 72):
        super().__init__(
            master, text=text, command=command, width=width,
            height=36, corner_radius=6, border_width=2,
            border_color=SURFACE, fg_color=SURFACE,
            hover_color=("#E5E5E5", "#3D3D3D"), text_color=TEXT,
        )
        tk.Frame.configure(self, takefocus=1)
        tk.Misc.bind(self, "<FocusIn>", self._focus_in, add="+")
        tk.Misc.bind(self, "<FocusOut>", self._focus_out, add="+")
        tk.Misc.bind(self, "<Return>", self._activate, add="+")
        tk.Misc.bind(self, "<space>", self._activate, add="+")
        self.bind("<Button-1>", self._mouse_focus, add="+")

    def focus_set(self):
        return tk.Misc.focus_set(self)

    def _mouse_focus(self, event):
        if self.cget("state") == "normal":
            self.focus_set()

    def _focus_in(self, event):
        if event.widget is self:
            self.configure(border_color=FOCUS)

    def _focus_out(self, event):
        if event.widget is self:
            self.configure(border_color=SURFACE)

    def _activate(self, event):
        if self.cget("state") == "normal":
            self.invoke()
        return "break"

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state="normal" if enabled else "disabled")
        tk.Frame.configure(self, takefocus=1 if enabled else 0)


class HoverHUD(ctk.CTkFrame):
    """Floating transport/curation toolbar over the preview stage. Placed
    (not gridded) so it never reserves layout space; a bounded 80ms poll
    tracks pointer/focus state rather than relying on CTk child enter/
    leave events (which flicker across composite widgets and would
    require replacing other widgets' bindings). Solid background, not
    falsely alpha-translucent — CTk's "transparent" paints the parent
    colour, and a second translucent Toplevel has real focus/DPI/capture
    costs (notes_006 §2.2)."""

    def __init__(
        self, stage, actions: dict[str, Callable[[], None]],
        *, idle_seconds: float = 2.5, always_visible: bool = False,
    ):
        super().__init__(
            stage, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER
        )
        self.stage = stage
        self.idle_seconds = max(0.1, idle_seconds)
        self.always_visible = always_visible
        self.pinned = False
        self.visible = False
        self._closed = False
        self._pointer = None
        self._last_activity = time.monotonic()
        self.buttons: dict[str, ActionButton] = {}
        for column, (name, callback) in enumerate(actions.items()):
            button = ActionButton(self, text=name, command=callback)
            button.grid(row=0, column=column, padx=3, pady=6)
            self.buttons[name] = button
        self._job = self.after(80, self._tick)

    def set_always_visible(self, value: bool) -> None:
        self.always_visible = value
        if value:
            self.reveal()

    def reveal(self, *, keyboard: bool = False) -> None:
        if self._closed:
            return
        self._last_activity = time.monotonic()
        if not self.visible:
            self.place(relx=0.5, rely=1.0, anchor="s", y=-12)
            self.lift()
            self.visible = True
        if keyboard:
            for button in self.buttons.values():
                if button.cget("state") == "normal":
                    button.focus_set()
                    break

    def _tick(self) -> None:
        self._job = None
        if self._closed:
            return
        now = time.monotonic()
        point = self.stage.winfo_pointerxy() if self.stage.winfo_ismapped() else None
        over_stage = pointer_inside(self.stage)
        if over_stage and point != self._pointer:
            self._last_activity = now
        self._pointer = point if over_stage else None
        held = (
            self.always_visible or self.pinned or pointer_inside(self)
            or contains_widget(self, self.focus_get())
        )
        if held or ((over_stage or self.visible) and now - self._last_activity < self.idle_seconds):
            if not self.visible:
                self.reveal()
        elif self.visible:
            self.place_forget()
            self.visible = False
        self._job = self.after(80 if self.stage.winfo_ismapped() else 400, self._tick)

    def destroy(self) -> None:
        if not self._closed:
            self._closed = True
            if self._job is not None:
                self.after_cancel(self._job)
                self._job = None
        super().destroy()


@dataclass(frozen=True)
class Notice:
    text: str
    error: bool = False
    action_text: str = ""
    action: Optional[Callable[[], None]] = None
    seconds: float = 4.0


class ToastManager(ctk.CTkFrame):
    """One visible compact card plus a bounded FIFO backlog (notes_006
    §2.5). Presentation only — dedup-by-event-key and activity-log
    ingestion belong at the call site, not here. post() returns False on
    overflow; the caller must keep its own persistent error indicator
    rather than assume a dropped toast was shown. Success toasts expire
    after >=4s unless hovered/focused/the window is unmapped; error/action
    toasts stay until dismissed."""

    def __init__(self, parent):
        super().__init__(
            parent, fg_color=SURFACE, corner_radius=10, border_width=1, border_color=BORDER
        )
        self._inbox: "queue.Queue[Notice]" = queue.Queue(maxsize=32)
        self._closed_event = threading.Event()
        self._active: Optional[Notice] = None
        self._remaining = 0.0
        self._last_tick = time.monotonic()
        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(
            self, text="", text_color=TEXT, justify="left", anchor="w", wraplength=250
        )
        self.label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")
        self.close_button = ActionButton(self, text="Dismiss", command=self.dismiss)
        self.close_button.grid(row=0, column=1, padx=(0, 8), pady=8)
        self.action_button = ActionButton(self, text="Action", command=self._act)
        self.action_button.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")
        self.action_button.grid_remove()
        self._job = self.after(100, self._tick)

    def post(self, notice: Notice) -> bool:
        if self._closed_event.is_set():
            return False
        try:
            self._inbox.put_nowait(notice)
        except queue.Full:
            LOG.warning("Toast backlog full: %s", notice.text)
            return False
        return True

    def _show(self, notice: Notice) -> None:
        self._active = notice
        self._remaining = max(4.0, notice.seconds)
        self.label.configure(text=notice.text, text_color=ERROR_TEXT if notice.error else TEXT)
        if notice.action is not None:
            self.action_button.configure(text=notice.action_text or "Action")
            self.action_button.grid()
        else:
            self.action_button.grid_remove()
        self.place(relx=1.0, x=-12, y=48, anchor="ne")
        self.lift()

    def _tick(self) -> None:
        self._job = None
        if self._closed_event.is_set():
            return
        now = time.monotonic()
        elapsed = min(now - self._last_tick, 0.25)
        self._last_tick = now
        if self._active is None:
            try:
                self._show(self._inbox.get_nowait())
            except queue.Empty:
                pass
        elif not self._active.error and self._active.action is None:
            held = (
                not self.winfo_toplevel().winfo_ismapped() or pointer_inside(self)
                or contains_widget(self, self.focus_get())
            )
            if not held:
                self._remaining -= elapsed
                if self._remaining <= 0:
                    self.dismiss()
        self._job = self.after(100, self._tick)

    def dismiss(self) -> None:
        if contains_widget(self, self.focus_get()):
            self.master.focus_set()
        self._active = None
        self.place_forget()

    def focus_notice(self) -> None:
        if self._active is not None:
            button = self.action_button if self._active.action else self.close_button
            button.focus_set()

    def _act(self) -> None:
        notice = self._active
        self.dismiss()  # avoid reusing an action during its own callback
        if notice is not None and notice.action is not None:
            try:
                notice.action()
            except Exception:
                LOG.exception("Notification action failed")
                self._show(Notice("Action failed. See activity details.", error=True))

    def destroy(self) -> None:
        if not self._closed_event.is_set():
            self._closed_event.set()
            if self._job is not None:
                self.after_cancel(self._job)
                self._job = None
            self._active = None
            while not self._inbox.empty():
                try:
                    self._inbox.get_nowait()
                except queue.Empty:
                    break
        super().destroy()


class TagSelector(ctk.CTkFrame):
    """Exact-canonical-string tag chips with autocomplete (notes_006
    §2.4/§4.4). One chip row per tag inside a bounded scroll region — more
    reliable than approximating pixel widths for a horizontal chip flow,
    and scales to long/localised names. Matching stays case-sensitive
    (preserving Desktop Vista's existing tag storage semantics); the
    component never casefolds or merges stored tags, only offers
    case-insensitive *search* while inserting the existing exact spelling.
    Storage is entirely external — the caller supplies known tags and
    receives change callbacks; this widget writes nothing to disk."""

    def __init__(
        self, parent, *, known: Iterable[str] = (),
        on_change: Callable[[tuple[str, ...]], None],
        on_filter: Callable[[str], None] = lambda tag: None,
        on_close_requested: Callable[[], None] = lambda: None,
    ):
        super().__init__(parent, fg_color="transparent")
        self._tags: list[str] = []
        self._known = tuple(dict.fromkeys(known))
        self._on_change = on_change
        self._on_filter = on_filter
        self._on_close_requested = on_close_requested
        self._remove_buttons: list[ActionButton] = []
        self._suggestion_buttons: list[ActionButton] = []
        self.grid_columnconfigure(0, weight=1)
        self.chips = ctk.CTkScrollableFrame(self, height=112)
        self.chips.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.chips.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(self, placeholder_text="Add a tag")
        self.entry.grid(row=1, column=0, padx=(0, 6), pady=8, sticky="ew")
        self.add_button = ActionButton(self, text="Add", command=self._commit)
        self.add_button.grid(row=1, column=1, pady=8)
        self.hint = ctk.CTkLabel(
            self, text="", anchor="w", justify="left", wraplength=300, text_color=TEXT
        )
        self.hint.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.suggestions = ctk.CTkFrame(self, fg_color="transparent")
        self.suggestions.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.suggestions.grid_columnconfigure(0, weight=1)
        self.entry.bind("<KeyRelease>", self._search, add="+")
        self.entry.bind("<Return>", self._commit_event, add="+")
        self.entry.bind("<Down>", self._down, add="+")
        self.entry.bind("<Escape>", self._escape, add="+")
        self.entry.bind("<BackSpace>", self._backspace, add="+")

    def get_tags(self) -> tuple[str, ...]:
        return tuple(self._tags)

    def set_tags(self, values: Iterable[str]) -> None:
        if contains_widget(self.chips, self.focus_get()) or contains_widget(
            self.suggestions, self.focus_get()
        ):
            self.entry.focus_set()
        self._tags = list(dict.fromkeys(v.strip() for v in values if v.strip()))
        self.entry.delete(0, "end")
        self.hint.configure(text="")
        self._clear_suggestions()
        self._render()

    def set_known(self, values: Iterable[str]) -> None:
        self._known = tuple(dict.fromkeys(values))

    def _render(self) -> None:
        for child in self.chips.winfo_children():
            child.destroy()
        self._remove_buttons.clear()
        for row, tag in enumerate(self._tags):
            pill = ctk.CTkFrame(self.chips, corner_radius=12, fg_color=SURFACE)
            pill.grid(row=row, column=0, sticky="ew", pady=3)
            pill.grid_columnconfigure(0, weight=1)
            label = tag if len(tag) <= 24 else tag[:21] + "..."
            choose = ActionButton(pill, text=label, command=lambda value=tag: self._filter(value))
            choose.grid(row=0, column=0, sticky="ew", padx=(4, 2))
            remove = ActionButton(pill, text="Remove", command=lambda value=tag: self.remove_tag(value))
            remove.grid(row=0, column=1, padx=(0, 4))
            tk.Misc.bind(
                choose, "<FocusIn>", lambda event, value=tag: self.hint.configure(text=value), add="+"
            )
            tk.Misc.bind(
                remove, "<FocusIn>",
                lambda event, value=tag: self.hint.configure(text="Remove tag: " + value), add="+",
            )
            self._remove_buttons.append(remove)

    def _filter(self, tag: str) -> None:
        self.hint.configure(text=tag)
        self._on_filter(tag)

    def add_tag(self, value: str) -> None:
        value = value.strip()
        if not value:
            self.hint.configure(text="Enter a tag first.")
            return
        if value in self._tags:
            self.hint.configure(text="This tag is already selected.")
            return
        self._tags.append(value)
        self._render()
        self.entry.delete(0, "end")
        self._clear_suggestions()
        self.hint.configure(text="Added: " + value)
        self.entry.focus_set()
        self._on_change(self.get_tags())

    def remove_tag(self, value: str) -> None:
        if value not in self._tags:
            return
        self._tags.remove(value)
        self.entry.focus_set()  # move focus before destroying its old Remove button
        self._render()
        self.hint.configure(text="Removed: " + value)
        self._on_change(self.get_tags())

    def _commit(self) -> None:
        self.add_tag(self.entry.get())

    def _commit_event(self, event):
        self._commit()
        return "break"

    def _clear_suggestions(self) -> None:
        for child in self.suggestions.winfo_children():
            child.destroy()
        self._suggestion_buttons.clear()

    def _search(self, event=None):
        if event is not None and event.keysym in ("Down", "Escape", "Return", "Tab"):
            return
        self._clear_suggestions()
        query = self.entry.get().strip().casefold()
        matches = (
            []
            if not query
            else sorted(
                (tag for tag in self._known if query in tag.casefold() and tag not in self._tags),
                key=str.casefold,
            )[:6]
        )
        for row, tag in enumerate(matches):
            label = tag if len(tag) <= 24 else tag[:21] + "..."
            button = ActionButton(self.suggestions, text=label, command=lambda value=tag: self.add_tag(value))
            button.grid(row=row, column=0, sticky="ew", pady=2)
            tk.Misc.bind(button, "<Escape>", self._escape_suggestions, add="+")
            tk.Misc.bind(
                button, "<FocusIn>", lambda event, value=tag: self.hint.configure(text=value), add="+"
            )
            self._suggestion_buttons.append(button)
        if query and not matches:
            self.hint.configure(text="Enter or Add creates this tag.")

    def _down(self, event):
        if self._suggestion_buttons:
            self._suggestion_buttons[0].focus_set()
        return "break"

    def _escape(self, event):
        if self._suggestion_buttons:
            self._clear_suggestions()
        else:
            self._on_close_requested()
        return "break"

    def _escape_suggestions(self, event):
        self.entry.focus_set()
        self._clear_suggestions()
        return "break"

    def _backspace(self, event):
        if not self.entry.get() and self._remove_buttons:
            self._remove_buttons[-1].focus_set()
            return "break"
        return None
