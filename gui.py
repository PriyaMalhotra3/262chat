#!/usr/bin/env python

from customtkinter import *
from tkinter import messagebox
import asyncio
import sys
from os import path
from datetime import datetime

from interface import Message, AbstractSession
from part1.client import Session as Part1Session
from part2.client import Session as Part2Session

set_appearance_mode("dark")

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

class AnnotatedText(CTkFrame):
    def __init__(self, parent, text):
        super().__init__(
            master=parent,
            fg_color="transparent",
        )
        WrapLabel(
            self,
            text=text,
            justify="left",
            compound="left",
            anchor=W
        ).pack(
            fill=X
        )

    def annotate(self, title, body):
        text = title + ": "
        if isinstance(body, list):
            text += ", ".join(body)
        elif isinstance(body, datetime):
            text += body.strftime("%c")
        else:
            text += str(body)
        WrapLabel(
            self,
            font=CTkFont(
                size=10
            ),
            text=text,
            justify="left",
            compound="left",
            anchor=W
        ).pack(
            fill=X
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
        asyncio.create_task(self.update_users())
        self.to.bind("<KeyRelease>", lambda event: asyncio.create_task(self.update_users(event)))
        self.draft = CTkTextbox(
            master=self,
            wrap="word"
        )
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
            command=lambda: asyncio.create_task(self.send(self.users, self.draft.get("1.0", "end")))
        ).grid(
            row=1,
            column=3,
            padx=(10, 32),
            pady=(10, 32)
        )

        asyncio.create_task(self.consume())

    def add_message(self, name: str, text: str):
        row = self.messages.grid_size()[1]
        CTkLabel(
            master=self.messages,
            text=name,
            font=CTkFont(
                weight="bold"
            )
        ).grid(
            row=row,
            column=0,
            sticky=N
        )

        handle = AnnotatedText(
            self.messages,
            text
        )
        handle.grid(
            row=row,
            column=1,
            sticky=EW
        )
        return handle

    async def consume(self):
        async for message in self.session.stream():
            handle = self.add_message(message.to, message.text)
            if message.sent is not None:
                handle.annotate("Sent", message.sent)

    async def send(self, to, text):
        display = self.add_message(self.session.username, text)
        await asyncio.gather(*(
            self.session.message(Message(
                to=user.split(maxsplit=1)[0],
                text=text
            ))
            for user in to
        ))
        display.annotate("Sent", datetime.now())

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
        if event is not None:
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

        self.geometry("400x300")
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
            button.configure(command=lambda source=button: asyncio.create_task(self.connect(source)))

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
            self.withdraw()
            Chat(session)
        except Exception as e:
            messagebox.showerror("Error", str(e))
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
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    if len(sys.argv) < 2 or sys.argv[1] == "part1":
        from part1.client import Session
    elif sys.argv[1] == "part2":
        from part2.client import Session
    else:
        print("usage: python gui.py [part1|part2]", file=sys.stderr)
        sys.exit()
    app = App()
    app.mainloop()
