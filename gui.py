from customtkinter import *

from part1.client import *

class Chat(CTkToplevel):
    def __init__(self):
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
        self.host = CTkEntry(
            server_frame,
            placeholder_text="Host"
        ).pack(side=LEFT, fill=BOTH, expand=True)
        self.port = CTkEntry(
            server_frame,
            placeholder_text="Port"
        ).pack(side=LEFT, fill=BOTH, expand=True)

        self.tabview = CTkTabview(self)
        self.tabview.pack(fill=BOTH, expand=True)
        tabs = [
            self.tabview.add("Register"),
            self.tabview.add("Login")
        ]
        for tab in tabs:
            tab.grid_columnconfigure(1, weight=1)

            CTkLabel(tab, "Username: ").grid(row=0,column=0)
            username = StringVar()
            CTkEntry(tab, textvariable=username).grid(row=0, column=1)
            CTkLabel(tab, "Password: ").grid(row=1,column=0)
            password = StringVar()
            CTkEntry(tab, textvariable=password, show="•").grid(row=0, column=1)

            CTkButton(
                tab,
                "Start",
                command=lambda: self.initiate(username.get(), password.get())
            ).grid(
                row=0, column=0,
                columnspan=2
            )

    def initiate(self, username, password):
        async def conect(create=False):
            session = await Session.connect(self.host.get(), int(self.port.get()))
            if create:
                await session.register(username)
            else:
                await session.login(password)
        
        if self.tabview.get() == "Register":
            
        else:
        Chat()
        self.withdraw()

async def main():
    app = App()
    while True:
        app.update()
        await asyncio.sleep(0.1)
        
asyncio.run(main())
