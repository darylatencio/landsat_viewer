import tkinter as tk

#--------------------------------------------------------------------------------------------------
#+
#-
class login:

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def __init__(self, labels=None):
        self.tlb = tk.Tk()
        self.tlb.title("Login Information")
        self.labels = ["Username", "Password"] if (labels == None) else labels
        self.text = []
        for i, label in enumerate(self.labels):
            tk.Label(self.tlb, text=label+":").grid(column=0, padx=5, pady=5, row=i)
            entry = tk.Entry(self.tlb, width=80)
            entry.grid(column=1, padx=5, pady=5, row=i)
            self.text.append(entry)
        self.cb_value = tk.BooleanVar()
        checkbox = tk.Checkbutton(self.tlb, text="Save Login", variable=self.cb_value)
        checkbox.grid(column=0, row=len(self.labels))
        self.button = tk.Button(self.tlb, command=self.event_button, text="Login")
        self.button.grid(column=1, pady=10, row=len(self.labels))
        self.login = {}
        self.save = False
        self.tlb.wait_window(self.tlb)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def event_button(self):
        for i, label in enumerate(self.labels):
            self.login[label] = self.text[i].get()
        self.save = self.cb_value.get()
        self.tlb.destroy()

#--------------------------------------------------------------------------------------------------
#+
#-
def get_ee_login():
    l = ["Username","Token"]
    dialog = login(labels=l)
    uname, tok, save = "", "", False
    if dialog.login:
        uname, tok = dialog.login[l[0]], dialog.login[l[1]]
        save = dialog.save
    return uname, tok, save

#--------------------------------------------------------------------------------------------------
#+
#-
def test_login_dialog():
    uname, tok, save = get_ee_login()
    print(f"User: {uname}\nToken: {tok}")
    print(f"Save: {save}")

if (__name__ == "__main__"):
    test_login_dialog()