from customtkinter import *

from part1.client import *

class Chat(CTkToplevel):
    def __init__(self, session: Session):
        super().__init__()

        

class App(CTk):
    def __init__(self):
        super().__init__()

        self.geometry("400x300")
        self.title("262chat")

        CTkLabel(
            self,
            "Welcome to 262chat!",
            font=CTkFont(
                weight="bold",
                size=100
            )
        ).pack()
        CTkLabel(
            self,
            "by Priya Malhotra and Lawrence Bjerkestrand",
            font=CTkFont(slant="italic")
        ).pack()

        server_frame = CTkFrame(self)
        server_frame.pack(fill=X)
        CTkLabel(server_frame, "Server: ").pack(side=LEFT)
        host = CTkEntry(
            server_frame,
            placeholder_text="Host"
        ).pack(side=LEFT, fill=BOTH, expand=True)
        port = CTkEntry(
            server_frame,
            placeholder_text="Port"
        ).pack(side=LEFT, fill=BOTH, expand=True)

        tabview = CTkTabview(self)
        tabview.pack(fill=BOTH, expand=True)
        for tabname in ["Register", "Login"]:
            tab = tabview.add(tabname)
            tab.grid_columnconfigure(1, weight=1)

            CTkLabel(tab, "Username: ").grid(row=0,column=0)
            username = CTkEntry(tab, textvariable=username)
            username.grid(row=0, column=1)
            CTkLabel(tab, "Password: ").grid(row=1,column=0)
            password = CTkEntry(tab, textvariable=password, show="•")
            password.grid(row=0, column=1)
            button = CTkButton(tab, "Connect").grid(row=0, column=0, columnspan=2)

            async def connect():
                button.configure(state="disabled")
                tabview.configure(state="disabled")
                try:
                    session = await Session.connect(host.get(), int(port.get()))
                    if tabname == "Register":
                        endpoint = session.register
                    else:
                        endpoint = session.login
                    await endpoint(username.get(), password.get())
                    self.withdraw()
                    Chat(session)
                except (ValueError, ChatException) as e:
                    messagedialog.showerror("Error", e.args[0])
                    tabview.configure(state="enabled")
                    button.configure(state="enabled")
            button.configure(command=lambda: asyncio.create_task(connect()))

    def mainloop(self):
        async def loop():
            while True:
                app.update()
                await asyncio.sleep(0.1)
        asyncio.run(loop())

app = App()
app.mainloop()
