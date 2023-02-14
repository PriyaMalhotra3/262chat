from tkinter import TclError, messagebox
from customtkinter import *

from part1.client import *

set_appearance_mode("dark")

class Chat(CTkToplevel):
    def __init__(self, session: Session):
        super().__init__()

class App(CTk):
    def __init__(self):
        super().__init__()
        self.destroyed = False

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

        username = StringVar()
        password = StringVar()
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
                textvariable=username
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
                textvariable=password
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

    async def connect(self, source):
        source.configure(state="disabled")
        self.tabview.configure(state="disabled")
        try:
            try:
                port = int(self.port.get())
            except ValueError:
                raise ValueError("Port must be an integer.")
            session = await Session.connect(self.host.get(), port)
            if self.tabview.get() == "Register":
                endpoint = session.register
            else:
                endpoint = session.login
            await endpoint(username, password)
            self.withdraw()
            Chat(session)
        except Exception as e:
            print(e)
            messagebox.showerror("Error", str(e))
            source.configure(state="normal")
            self.tabview.configure(state="normal")

    def mainloop(self):
        async def loop():
            try:
                while not self.destroyed:
                    self.update()
                    await asyncio.sleep(0.01)
            except TclError:
                pass
        asyncio.run(loop())

    def destroy(self):
        destroy_now = super().destroy
        async def async_destroy():
            self.destroyed = True
            destroy_now()
        asyncio.create_task(async_destroy())

app = App()
app.mainloop()
