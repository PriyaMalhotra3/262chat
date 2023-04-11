#!/usr/bin/env python3

import sys
import asyncio
import colorsys
import tkinter
import traceback
from tkinter import messagebox
from customtkinter import *
from datetime import datetime
from zlib import crc32
from grpc import RpcError

from interface import Message, AbstractSession
from part1.client import Session as Part1Session
from part2.client import Session as Part2Session

set_appearance_mode("dark")

def format_time(t: datetime) -> str:
    return str(
        t.astimezone().replace(microsecond=0)
        - datetime.now().astimezone().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
    )

def user_color(username:str) -> str:
    # Hash username to a hue:
    hue = float(crc32(username.encode("utf-8")) & 0xffffffff)/2**32
    return "#" + "".join(
        f"{int(component*255):X}"
        for component in colorsys.hls_to_rgb(hue, 2/3, 1/3)
    )

def create_task(coro):
    async def wrapper(coro):
        try:
            await coro
        except RpcError as e:
            messagebox.showerror("Error", e.details())
        except Exception as e:
            messagebox.showerror("Error", str(e))
    asyncio.create_task(wrapper(coro))

class WrapLabel(CTkLabel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(
            master=parent,
            *args,
            **kwargs
        )
        self.bind("<Configure>", lambda _: self.configure(
            wraplength=self.winfo_width()
        ))

class Menubar(tkinter.Menu):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(
            master=parent,
            activebackground="gray10",
            background="gray14",
            activeforeground="gray84",
            foreground="gray84",
            borderwidth=0,
            activeborderwidth=0,
            relief="flat",
            tearoff=False,
            *args,
            **kwargs
        )

class Menu(tkinter.Menu):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(
            master=parent,
            activebackground="gray28",
            background="gray20",
            activeforeground="gray84",
            foreground="gray84",
            borderwidth=5,
            activeborderwidth=0,
            relief="flat",
            tearoff=False,
            *args,
            **kwargs
        )

class Chat(CTkToplevel):
    def __init__(self, session: AbstractSession):
        super().__init__()
        self.session = session

        self.geometry("600x600")
        self.title("262chat")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.messages = CTkScrollableFrame(
            master=self,
            fg_color="transparent"
        )
        self.messages.grid_columnconfigure(1, weight=1)
        self.messages.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky=NSEW,
            padx=32,
            pady=(32, 10)
        )
        CTkLabel(
            master=self,
            text="To:"
        ).grid(
            row=1,
            column=0,
            padx=(32, 0),
            pady=(10, 32)
        )
        self.pattern = StringVar(value="*")
        self.to = CTkComboBox(
            master=self,
            values=[],
            variable=self.pattern
        )
        self.to.grid(
            row=1,
            column=1,
            padx=10,
            pady=(10, 32)
        )
        create_task(self.update_users())
        self.to.bind("<KeyRelease>", lambda event: create_task(self.update_users(event)))
        self.draft = CTkTextbox(
            master=self,
            wrap="word",
            height=10
        )
        self.draft.bind("<Shift-Return>", self.ship_draft)
        self.draft.bind("<Control-Return>", self.ship_draft)
        self.draft.bind("<KeyRelease>", self.resize_draft)
        self.draft.grid(
            row=1,
            column=2,
            sticky=EW,
            padx=10,
            pady=(10, 32)
        )
        CTkButton(
            master=self,
            text="Send",
            command=self.ship_draft
        ).grid(
            row=1,
            column=3,
            padx=(10, 32),
            pady=(10, 32),
            sticky=NS
        )

        menubar = Menubar(self)
        account_menu = Menu(menubar)
        account_menu.add_command(label="Logout", command=self.destroy)
        account_menu.add_separator()
        account_menu.add_command(label="Delete account...", command=self.delete_account)
        menubar.add_cascade(label="Account ", menu=account_menu)
        self.configure(menu=menubar)

        create_task(self.consume())

    def delete_account(self):
        async def delete_and_quit():
            await self.session.delete()
            self.destroy()
        if messagebox.askyesno(
                "Delete Account",
                "Are you sure you want to delete your 262chat account? This operation cannot be undone."
        ):
            create_task(delete_and_quit())

    def ship_draft(self, event=None):
        create_task(self.send())

    def resize_draft(self, event=None):
        self.draft.configure(
            height=min(200, 16*float(self.draft.index("end")))
        )

    def add_message(self, username: str, text: str):
        row = self.messages.grid_size()[1]
        CTkLabel(
            master=self.messages,
            text=username,
            text_color="#FFFFFF" if username == self.session.username else user_color(username),
            font=CTkFont(
                weight="bold"
            ),
            justify="right",
            compound="right",
            anchor=E
        ).grid(
            row=row,
            column=0,
            sticky=NE,
            padx=(0, 10)
        )

        WrapLabel(
            self.messages,
            text=text,
            justify="left",
            compound="left",
            anchor=W
        ).grid(
            row=row,
            column=1,
            sticky=N+EW,
            pady=(5, 0)
        )

        time = CTkLabel(
            master=self.messages,
            font=CTkFont(
                size=11
            )
        )
        time.grid(
            row=row,
            column=2,
            sticky=NE,
            padx=10
        )
        self.messages._parent_canvas.yview_moveto(1.0)
        return time

    async def consume(self):
        async for message in self.session.stream():
            time = self.add_message(message.to, message.text)
            if message.sent:
                time.configure(text=format_time(message.sent))

    async def send(self):
        text = self.draft.get("1.0", "end")
        self.draft.delete("1.0", "end")
        self.resize_draft()
        if not text.strip():
            return
        time = self.add_message(self.session.username, text)
        await asyncio.gather(*(
            self.session.message(Message(
                to=user.split(maxsplit=1)[0],
                text=text
            ))
            for user in self.users
        ))
        time.configure(text=format_time(datetime.now()))

    async def update_users(self, event=None):
        self.users = await self.session.list_users(self.pattern.get())
        try:
            self.users.remove(self.session.username)
        except ValueError:
            pass
        try:
            self.users.remove(self.session.username + " (online)")
        except ValueError:
            pass
        self.to.configure(values=self.users)
        if event:
            try:
                self.to._open_dropdown_menu()
            except Exception:
                pass

    def destroy(self):
        super().destroy()
        os._exit(0)

class App(CTk):
    def __init__(self):
        super().__init__()

        self.geometry("600x600")
        self.title("262chat")

        CTkLabel(
            master=self,
            text="Welcome to 262chat!",
            font=CTkFont(
                weight="bold",
                size=48
            )
        ).pack(pady=(32, 0))
        CTkLabel(
            master=self,
            text="by Priya Malhotra and Lawrence Bjerkestrand",
            font=CTkFont(
                slant="italic",
                size=14
            )
        ).pack()

        server_frame = CTkFrame(master=self)
        server_frame.pack(
            fill=X,
            padx=32,
            pady=20,
            ipadx=10,
            ipady=10
        )
        CTkLabel(
            master=server_frame,
            text="Server:"
        ).pack(
            side=LEFT,
            padx=(16, 0)
        )
        self.host = CTkEntry(
            master=server_frame,
            placeholder_text="Host"
        )
        self.host.pack(
            side=LEFT,
            fill=X,
            expand=True,
            padx=10
        )
        self.port = CTkEntry(
            master=server_frame,
            placeholder_text="Port"
        )
        self.port.pack(
            side=LEFT,
            fill=X,
            expand=True,
            padx=10
        )
        self.port.bind("<KeyRelease>", self.checkport)
        self.part2 = CTkSwitch(
            master=server_frame,
            text="gRPC"
        )
        self.part2.pack(
            side=LEFT,
            padx=(10, 0)
        )

        self.username = StringVar()
        self.password = StringVar()

        self.tabview = CTkTabview(master=self)
        self.tabview.pack(
            fill=BOTH,
            expand=True,
            padx=32,
            pady=(0,48),
        )
        for tab in [self.tabview.add("Register"),
                    self.tabview.add("Login")]:
            tab.grid_columnconfigure(1, weight=1)

            CTkLabel(
                master=tab,
                text="Username:"
            ).grid(
                row=0,
                column=0,
                sticky=W,
                padx=10
            )
            CTkEntry(
                master=tab,
                textvariable=self.username
            ).grid(
                row=0,
                column=1,
                sticky=EW,
                pady=10
            )
            CTkLabel(
                master=tab,
                text="Password:"
            ).grid(
                row=1,
                column=0,
                sticky=W,
                padx=10
            )
            CTkEntry(
                master=tab,
                show="•",
                textvariable=self.password
            ).grid(
                row=1,
                column=1,
                sticky=EW,
                pady=10
            )

            button = CTkButton(
                master=tab,
                text="Connect"
            )
            button.grid(
                row=2,
                column=0,
                columnspan=2,
                sticky=NSEW,
                padx=10,
                pady=10,
                ipadx=5,
                ipady=5
            )
            button.configure(command=lambda source=button: create_task(self.connect(source)))

    def checkport(self, event):
        i = 0
        for char in self.port.get():
            if not char.isdecimal():
                self.port.delete(i)
            else:
                i += 1

    async def connect(self, source):
        source.configure(state="disabled")
        self.tabview.configure(state="disabled")
        try:
            try:
                port = int(self.port.get())
            except ValueError:
                raise ValueError("Port must be an integer.")
            if self.part2.get() == 1:
                implementation = Part2Session
            else:
                implementation = Part1Session
            session = await implementation.connect(self.host.get(), port)
            if self.tabview.get() == "Register":
                endpoint = session.register
            else:
                endpoint = session.login
            await endpoint(self.username.get(), self.password.get())
        except:
            raise
        else:
            self.withdraw()
            Chat(session)
        finally:
            self.tabview.configure(state="normal")
            source.configure(state="normal")

    def mainloop(self):
        async def loop():
            while True:
                try:
                    self.update()
                    await asyncio.sleep(0.01)
                except Exception as e:
                    print(e, file=sys.stderr)
        asyncio.run(loop())

    def destroy(self):
        super().destroy
        os._exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()
