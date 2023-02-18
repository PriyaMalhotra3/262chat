#!/usr/bin/env python

from customtkinter import *
from tkinter import messagebox
import asyncio
import sys
from os import path
import traceback

from interface import Message, AbstractSession
from part1.client import Session as Part1Session
from part2.client import Session as Part2Session

set_appearance_mode("dark")

class Chat(CTkToplevel):
    class DisplayedMessage:
        def __init__(self, parent, message: Message):
            row = parent.grid_size()[1]
            self.label = CTkLabel(
                master=parent
            )
            self.label.grid(
                row=row,
                column=0
            )

            text_time = CTkFrame(
                master=parent,
                fg_color="transparent"
            )
            text_time.grid(
                row=row,
                column=1
            )

            self.message = message
            self.sent = sent

        @property
        def sent(self):
            return self.message.sent

        @sent.setter
        def sent(self, sent):
            self.message.sent = sent

    def __init__(self, session: AbstractSession):
        super().__init__()
        self.session = session

        self.geometry("600x600")
        self.title("262chat")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=0)
        self.messages = CTkScrollableFrame(master=self)
        self.messages.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky=NSEW,
            padx=32,
            pady=(32, 10)
        )
        self.pattern = StringVar(value="*")
        self.to = CTkComboBox(
            master=self,
            values=["Alice", "Bob"],
            variable=self.pattern
        )
        self.to.grid(
            row=1,
            column=0,
            padx=(32, 10),
            pady=(10, 32)
        )
        asyncio.create_task(self.update_users())
        self.to.bind("<KeyRelease>", lambda event: asyncio.create_task(self.update_users(event)))
        self.draft = CTkEntry(
            master=self
        )
        self.draft.grid(
            row=1,
            column=1,
            sticky=EW,
            padx=10,
            pady=(10, 32)
        )
        CTkButton(
            master=self,
            text="Send"
        ).grid(
            row=1,
            column=2,
            padx=(10, 32),
            pady=(10, 32)
        )

        asyncio.create_task(self.consume())

    async def consume(self):
        async for message in self.session.stream():
            # self.DisplayedMessage(self, message)
            pass

    async def send(self, text, to):
        payload = Message(to=to, text=text, sent=None)
        handle = self.DisplayedMessage(self, payload)
        await self.session.message(payload)
        handle.message = Message(to=to, text=text, sent=datetime.now())

    async def update_users(self, event=None):
        users = await self.session.list_users(self.pattern.get())
        self.to.configure(values=users)
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
            print(traceback.format_exc())
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
