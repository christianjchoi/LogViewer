from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import os, re, platform, codecs

# Log Viewer: Tool for Highlighting, Filtering, & Navigating to Text
# @author Christian Choi

root = Tk()

# allows right click copy and paste functionality
def copypaste(entry):
	widget = entry.widget
	menu = Menu(root, tearoff = 0)
	menu.add_command(label = "Cut")
	menu.add_separator()
	menu.add_command(label = "Copy")
	menu.add_separator()
	menu.add_command(label = "Paste")
	menu.add_separator()
	menu.entryconfigure("Cut", \
		command = lambda: widget.event_generate("<<Cut>>"))
	menu.entryconfigure("Copy", \
		command = lambda: widget.event_generate("<<Copy>>"))
	menu.entryconfigure("Paste", \
		command = lambda: widget.event_generate("<<Paste>>"))
	menu.tk.call("tk_popup", menu, entry.x_root, entry.y_root)

# sets up menu
menu = Menu(root)
root.config(menu = menu)


# sets textbox width depending on screen resolution
def width():
	w = root.winfo_screenwidth()
	if w >= 1920:
		return 259
	elif 1366 <= w < 1920:
		return 222
	elif 1280 <= w < 1366:
		return 208
	else:
		return 127

# sets textbox height depending on screen resolution
def height():
	h = root.winfo_screenheight()
	if h >= 1080:
		return 74
	elif 768 <= h < 1080:
		return 44
	elif 720 <= h < 768:
		return 41
	else:
		return 32

# main class for this application
class Application(Frame):

	# string of every line in a file we display
	lines = ['']

	# possible highlight colors we cycle through during line highlight
	colors = ["yellow", "orange", "deep pink", "chartreuse",
		"cyan", "magenta", "gold", "salmon", "aquamarine", "red",
		"peach puff", "navajo white", "lemon chiffon",
		"honeydew", "gray", "lavender", "lavender blush", "misty rose",
		"cornflower blue", "light slate blue", "dodger blue", "deep sky blue",
		"light steel blue", "pale turquoise", "dark turquoise",
		"light sea green", "spring green", "medium spring green",
		"lime green","goldenrod", "indian red", "firebrick", "light coral",
		"hot pink", "violet", "purple"]

	# number of successful highlight operations
	highlights = 0

	# color of keyword in the search string box
	keycolors = {}

	# mapping from line to list of colors, denoting its color history
	linetocolors = {}

	# mapping from color to list of lines, denoting lines of each color
	colortolines = {}

	# highlighted key words or regex patterns in the legend box
	searchstrings = []

	# name of file we display
	filelabel = None

	# bookmark lines
	bookmarked = []

	# lines where we are at on screen for each color
	currentlines = {}

	# directory initially cwd
	directory = os.getcwd()

	# mappings from color to jump label 
	text = {}

	# version number
	vnum = 2.0

	# max # lines per file we load onto display, if exceeds we split into new files
	splitlimit = 15000


	def __init__(self, master):

		# initialize the frame
		Frame.__init__(self, master)
		self.pack(expand = YES, fill = BOTH)
		self.master.title("Log Viewer")

		# frame 1
		self.topframe = Frame(master)
		self.topframe.pack(expand = YES, fill = BOTH, side = TOP)
		
		# frame 2
		self.middleframe = Frame(master)
		self.middleframe.pack(expand = YES, fill = BOTH, side = TOP)

		# frame 3
		self.bottomframe = Frame(master)
		self.bottomframe.pack(expand = YES, fill = BOTH, side = TOP)

		# key entry widget
		self.keyword = Label(self.topframe, text = "  Keyword:  ")
		self.keyentry = Entry(self.topframe, width = 1)
		self.keyword.pack(side = LEFT)
		self.keyentry.pack(expand = YES, fill = X, side = LEFT)
		self.keyentry.bind_class("Entry", "<Button-3><ButtonRelease-3>", copypaste)

		# checkbutton option for ignoring the case
		self.ignorecase = BooleanVar()
		self.entrycase = Checkbutton(self.topframe, text = "Ignore Case", variable = self.ignorecase)
		self.entrycase.pack(expand = NO, side = LEFT)

		self.searchonly = BooleanVar()
		self.entrysearchonly = Checkbutton(self.topframe, text = "Search Only", variable = self.searchonly)
		self.entrysearchonly.pack(expand = NO, side = LEFT)

		# regex checkbox for option to search regex instead of a keywordchir
		self.regex = BooleanVar()
		self.doregex = Checkbutton(self.topframe, text = "Regex", variable = self.regex)
		self.doregex.pack(expand = NO, side = LEFT)

		# search botton
		self.keysearch = Button(self.topframe, text = "  Search  ", command = self.highlight)
		self.keysearch.pack(expand = NO, side = LEFT)

		self.disablebutton = Button(self.topframe, text = "  Configure Matches  ")
		self.disablebutton.pack(expand = NO, side = LEFT, padx = 10)

		self.jumpbutton = Button(self.topframe, text = "  Jump to Matches  ")
		self.jumpbutton.pack(expand = NO, side = LEFT)

		self.bmarkline = Label(self.topframe, text = "  Line:  ")
		self.bmarkline.pack(expand = NO, side = LEFT)

		self.bmarkentry = Entry(self.topframe, width = 5)
		self.bmarkentry.pack(expand = NO, side = LEFT)

		self.bmarkgo = Button(self.topframe, text = "  Go  ")
		self.bmarkgo.pack(expand = NO, side = LEFT, padx = 5)


		# bound event function for highlighting
		def keyboardhighlight(event):
			self.highlight()

		# bind above function to Return Key
		self.keyentry.bind("<Return>", keyboardhighlight)
	
		# our two dropdown menus with command
		self.submenu = Menu(menu, tearoff = 0)
		self.bookmarks = Menu(menu, tearoff = 0)
		self.version = Menu(menu, tearoff = 0)

		menu.add_cascade(label = "File", menu = self.submenu)
		menu.add_cascade(label = "Bookmarks", menu = self.bookmarks)
		menu.add_cascade(label = "Version", menu = self.version)

		self.version.add_separator()
		self.version.add_command(label = Application.vnum)
		self.version.add_separator()

		# adjust the max # lines loaded onto display and per file split
		def setlimit():
			menu = Toplevel()
			menu.title("Split File")
			menu.focus_set(), menu.grab_set()
			topframe, midframe, bottomframe = Frame(menu), Frame(menu), Frame(menu)
			topframe.pack(expand = YES, fill = BOTH, side = TOP)
			midframe.pack(expand = YES, fill = BOTH, side = TOP)
			bottomframe.pack(expand = YES, fill = BOTH, side = TOP)
			current = Label(topframe, text = "Current: %d" % (Application.splitlimit))
			current.pack(expand = YES, fill = BOTH, side = TOP)
			Label(midframe, text = "# Lines Per File: ").pack(expand = YES, fill = BOTH, side = LEFT)
			e = Entry(midframe)
			e.pack(expand = YES, fill = BOTH, side = TOP)

			def submit():
				n = e.get().strip()
				e.delete(0, END)
				if not n.isdigit():
					messagebox.showinfo("Note", "Must be a number.")
					return
				elif int(n) < 5000:
					messagebox.showinfo("Note", "Minimum is 5000.")
					return
				Application.splitlimit = int(n)
				current.config(text = "Current: %d" % (Application.splitlimit))

			Button(bottomframe, text = "Set Limit", command = submit).pack(expand = YES, fill = BOTH, pady = 5)


		self.submenu.add_separator()
		self.submenu.add_command(label = "Open File", command = self.look)
		self.submenu.add_separator()
		self.submenu.add_command(label = "Save Configuration", command = self.savesearch)
		self.submenu.add_separator()
		self.submenu.add_command(label = "Load Configuration", command = self.loadsearch)
		self.submenu.add_separator()
		self.submenu.add_command(label = "Set File Lines Limit", command = setlimit)
		self.submenu.add_separator()

		self.submenu.add_command(label = "Exit", command = lambda: root.quit())
		self.submenu.add_separator()
		
		# lines of file shown in textbox in frame
		self.box = Text(self.middleframe, wrap = NONE, height = height(), width = width(),\
			font = ("Times, 8"))
		self.scrollbar = Scrollbar(self.middleframe)
		self.box.config(yscrollcommand = self.scrollbar.set)
		self.scrollbar.config(command = self.box.yview)
		self.box.pack(expand = YES, fill = BOTH, side = LEFT)
		self.scrollbar.pack(expand = YES, fill = BOTH, side = LEFT)
		self.box.bind_class("Text", "<Button-3><ButtonRelease-3>", copypaste)
		self.box.config(state = DISABLED)
		self.horizbar = Scrollbar(self.bottomframe, orient = HORIZONTAL)
		self.horizbar.config(command = self.box.xview)
		self.horizbar.pack(expand = YES, fill = BOTH, side = BOTTOM)
		self.box.config(xscrollcommand = self.horizbar.set)


	# some class variables we need to keep track of temporary highlights
	matching, matchinglines = [], []
	pointer = 0
	firsttime = True
	unchanged = False

	# jumps to line when doing search only option with only temporary highlighting
	def jumpsearch(self, key, ignorecase):

		# reset some class variables
		Application.matching[:], Application.matchinglines[:] = [], []
		Application.pointer = 0
		Application.firsttime = True
		Application.unchanged = False

		# start search at line 1
		start = 1
		for line in Application.lines[1:]:
			oldline = line
			if ignorecase:
				line = line.lower()
			if (self.regex.get() and re.search(key, line)) or key in line:
				countvar = StringVar()
				pos = self.box.search(oldline, str(float(start)), END, count = countvar)
				if pos:
					Application.matching.append((pos, countvar))
					Application.matchinglines.append(self.box.get(pos, "%s + %sc" % (pos, countvar.get())))
					# increment search start position each time we have a match
					start = int(float(pos)) + 1
		if not Application.matching:
			messagebox.showinfo("Notice", "Key does not exist.")
			return

		# create popup to cycle through matches and temporarily highlight
		searchmenu = Toplevel()
		searchmenu.title(key)
		searchmenu.focus_set(), searchmenu.grab_set()
		frame = Frame(searchmenu)
		frame.pack(expand = YES, fill = BOTH)

		# what happens on an exit/close widget event
		def exit(tag, color):
			self.box.tag_config(tag, background = color, foreground = "black")
			searchmenu.destroy()

		# do the coloring of the line and update the line number on screen
		def docolor(tag, pos, countvar, label):
			self.box.tag_delete(tag) if tag in self.box.tag_names() else None 
			self.box.see(pos)
			self.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
			self.box.tag_config(tag, background = "black", foreground = "white")
			label["text"] = "\t" + str(int(float(pos))) + "\t  "

		
		# helper function to locate match and jump to it
		# previous: indicates if we're going forwards or backwards
		# colorandquit: only True when we need to recursively call function to get next color
		def locate(lab, previous = False, colorandquit = False):

			m, p = Application.matching, Application.pointer
	
			ml = Application.matchinglines
			pos, countvar = m[p][0], m[p][1]
			line = ml[p]
			# line may have a newline character at the end
			try:
				ix = Application.lines.index(line)
			except Exception:
				ix = Application.lines.index(line + "\n")
			if Application.linetocolors[ix]:
				prevcolor = Application.linetocolors[ix][-1]
			else:
				prevcolor = "white"
			# we will only do this when locate is called recursively
			if colorandquit:
				return prevcolor
			tag = pos.upper()
			if not Application.firsttime:
				self.box.tag_delete(tag) if tag in self.box.tag_names() else None 
				self.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
				self.box.tag_config(tag, background = prevcolor, foreground = "black")
			if lab["text"] == "\t \t":
				# protocol when closing the window
				searchmenu.protocol("WM_DELETE_WINDOW", lambda p1 = tag, p2 = prevcolor : exit(p1, p2))
				docolor(tag, pos, countvar, lab)
				Application.firsttime = False
				return
			# increment or decrement the pointer
			if not previous and p + 1 < len(m) - 1:
				Application.pointer += 1
			elif previous and p - 1 >= 0:
				Application.pointer -= 1
			else:
				return
			linepos, countvar = m[Application.pointer][0], m[Application.pointer][1]
			tag = linepos.upper()
			docolor(tag, linepos, countvar, label)
			# protocol when closing the window with the next color, fetched from recursive call
			currcolor = locate(lab, colorandquit = True)
			searchmenu.protocol("WM_DELETE_WINDOW", lambda p1 = tag, p2 = currcolor : exit(p1, p2))
		# end of helper function
		prev = Button(frame, text = "Previous")
		prev.pack(side = LEFT, expand = YES, fill = BOTH);
		label = Label(frame, text = "\t \t")
		label.pack(side = LEFT, expand = YES, fill = BOTH)
		nxt = Button(frame, text = "     Next    ")
		nxt.pack(side = LEFT, expand = YES, fill = BOTH)
		prev.config(command = lambda param = label: locate(param, previous = True))
		nxt.config(command = lambda param = label: locate(param))


	# open up file explorer to get the file
	def look(self):
		fname = filedialog.askopenfilename(initialdir = Application.directory, title = "Select file", \
			filetypes = (("All files", "*.*"), ("Txt files", ".txt"), ("Log files", ".log")))
		if fname == '':
			return
		try:
			f = open(fname, "r")
			Application.filelabel = fname
			self.master.title("Log Viewer | " + fname)
			Application.directory = os.path.dirname(fname)
		# you pressed cancel
		except TypeError:
			return
		self.printfile(f, fname)


	# when clicking on a bookmark, brings up the note associated with it
	def bmarkclick(self, line, msg):
		countvar = StringVar()
		pos = self.box.search(line, "0.0", END, count = countvar)
		if not pos or (line not in Application.lines and line + "\n" not in Application.lines):
			messagebox.showinfo("Note", "Either the line containing this bookmark was filtered \
				or the bookmark is for a different file.")
			return
		try:
			ix = Application.lines.index(line)
		except Exception:
			ix = Application.lines.index(line + "\n")
		if Application.linetocolors[ix]:
			currcolor = Application.linetocolors[ix][-1]
		else:
			currcolor = "white"
		tag = pos + " "
		self.box.see(str(float(pos)))
		self.box.tag_delete(tag) if tag in self.box.tag_names() else None 
		self.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
		self.box.tag_config(tag, background = "black", foreground = "white")
		# cycle through list to find the right bookmark tuple
		ix = 0
		for i in Application.bookmarked:
			if i[1] == line and i[2] == msg:
				break
			ix += 1
		label = Application.bookmarked[ix][0]
		# open up popup displaying the bookmark note
		notemenu = Toplevel()
		notemenu.title(label)
		notemenu.focus_set(), notemenu.grab_set()
		frame = Frame(notemenu)
		frame.pack(expand = YES, fill = BOTH)
		if msg == "" or msg.isspace():
			msg = "This bookmark has no note."
		Label(frame, text = msg.replace("\t", "\n") + "\t").pack(expand = YES, fill = BOTH)
		# function to call when the window is closed
		def exit():
			self.box.tag_config(tag, background = currcolor, foreground = "black")
			notemenu.destroy()
		notemenu.protocol("WM_DELETE_WINDOW", exit)


	# helper function to help select what unique color to highlight lines
	def colorselect(self, color = False):
		if not color:
			color = Application.colors[Application.highlights % len(Application.colors)]
		while color in self.popupinst.usedcolors:
			Application.highlights += 1
			color = Application.colors[Application.highlights % len(Application.colors)]
		return color

		
	# load search strings and bookmarks from a file
	def loadsearch(self, default = None, changedir = True):
		if self.filelabel is None:
			messagebox.showinfo("Notice", "No file to search is opened.")
			return
		if default is not None:
			fname = default
		else:
			fname = filedialog.askopenfilename(initialdir = Application.directory, title = "Select file", \
				filetypes = (("All files", "*.*"), ("Txt files", ".txt"), ("Log files", ".log")))
			if fname == '':
				return
			# prompt to set the default search strings to something new
			if "defaultsearchstrings.txt" not in fname:
				loadmenu = Toplevel()
				loadmenu.title("Set this file to the default file?")
				loadmenu.focus_set(), loadmenu.grab_set()
				frame = Frame(loadmenu)
				frame.pack(expand = YES, fill = BOTH)

				# creat the default file by copying over contents from loaded file
				def action(yes = True):
					deft = open("defaultsearchstrings.txt", "w+")
					with codecs.open(fname, "r", encoding ='utf-8', errors = 'ignore') as orig:
						[deft.write(line) for line in orig if yes]
					loadmenu.destroy()

				Label(frame, text = "Set this file to the default file?").pack(expand = YES, fill = BOTH)
				Button(frame, text = "Yes", command = action).pack(expand = YES, fill = BOTH)
				Button(frame, text = "No", command = lambda: action(yes = False)).pack(expand = YES, fill = BOTH)
		try:
			bmark = False
			f = codecs.open(fname, "r", encoding = "utf-8", errors = "ignore")
			for line in f:
				line = line.strip()
				# BOOKMARKS should be the last section in a search strings file
				if "BOOKMARKS" in line:
					bmark = True
					continue
				# proceed as usual if we have no yet hit a bookmark indicator
				content = re.search("(.*)<delim>", line).group(0)
				content = re.sub("<delim>", "", content)
				item = re.search("<delim>(.*)", line).group(0)[len("<delim>") : ]
				if not bmark:
					item = self.colorselect(color = item)
					self.highlight(key = content, load = True, color = item)
				else:
					# parse out the loaded file to get necessary bookmark information
					note, labelname = item.split("<delim2>")
					if labelname in [m[0] for m in Application.bookmarked]:
						messagebox.showinfo("Note", "Bookmark named '" + labelname + "' already exists.")
					else:
						countvar = StringVar()
						pos = self.box.search(content, "0.0", END, count = countvar)
						if pos:
							Application.bookmarked.append((labelname, content, note))
							self.bookmarks.add_command(label = labelname, command = \
								lambda p1 = content, p2 = note: self.bmarkclick(p1, p2))
							self.bookmarks.add_separator()
			# by default, update the directory to our last visited directory
			if changedir:
				Application.directory = os.path.dirname(fname)
		except Exception:
			return


	# saves search strings into a file, opens up file dialogue
	def savesearch(self):
		if Application.keycolors:
			f = filedialog.asksaveasfile(mode = 'w', defaultextension = ".txt")
			if f is None:
				return
			[f.write(string + "<delim>" + Application.keycolors[string] + "\n") \
				for string in Application.keycolors]
			# also saves bookmarks
			if Application.bookmarked:
				f.write("BOOKMARKS" + "\n")
				for each in Application.bookmarked:
					l, c, n = each
					# get rid of all newline chars to place writethis on a single line
					writethis = c.replace("\n", "") + "<delim>" + n.replace("\n", "\t") + "<delim2>" + l.strip()
					f.write(writethis + "\n")
		else:
			messagebox.showinfo("Notice", "No highlighted search strings to save.")


	# navigates to a line, has option to save this line as a bookmark
	def goline(self):
		bmark = self.bmarkentry.get().strip()
		self.bmarkentry.delete(0, END)
		if not bmark.isdigit():
			messagebox.showinfo("Notice", "Line must be a number.")
		# make sure line number is in range
		elif int(bmark) <= len(Application.lines[1:]):
			self.box.see(str(float(bmark)))
		else:
			messagebox.showinfo("Notice", "Line out of range.")


	# exports select highlighted text to file
	def export(self):
		if not self.popupinst.usedcolors:
			messagebox.showinfo("Notice", "No highlighted text to export.")
			return
		# open up selection panel to decide which keywords to export
		exportmenu = Toplevel()
		exportmenu.title("Choose lines of which color(s) to export to file")
		exportmenu.focus_set(), exportmenu.grab_set()
		[exportmenu.rowconfigure(i, weight = 1) for i in range(36)]
		frame = Frame(exportmenu)
		frame.pack(expand = YES, fill = BOTH)
		colorkeys = {}
		for key in self.keycolors:
			colorkeys[self.keycolors[key]] = key
		count = 0
		# check buttons to choose which lines to include
		self.varlst = [BooleanVar() for i in self.popupinst.usedcolors]
		for color in self.popupinst.usedcolors:
			key = colorkeys[color]
			check = Checkbutton(frame, text = key, bg = color, variable = self.varlst[count])
			check.pack(side = TOP, fill = BOTH, expand = YES)
			count += 1

		# helper function to decide which highlighted lines to include
		def tofile():
			if [i.get() for i in self.varlst] == [False for i in self.varlst]:
				messagebox.showinfo("Notice", "Nothing was selected.")
				return
			f = filedialog.asksaveasfile(mode='w', defaultextension=".txt")
			if f is None:
				return
			colordict, dic, ix  = {}, Application.linetocolors, 0
			for i in self.varlst:
				if i.get():
					colordict[self.popupinst.usedcolors[ix]] = []
				ix += 1
			[[colordict[color].append(linenum) for color in colordict if color in dic[linenum]] for linenum in dic]
			# do the writing to file
			f.write(Application.filelabel + '\n\n\n')
			for color in colordict:
				f.write("Keyword: " + colorkeys[color] + '\n\n')
				[f.write(str(linenum).rjust(6) + "\t" + Application.lines[int(linenum)]) for linenum in colordict[color]]
				f.write('\n\n')
			f.close()
			exportmenu.destroy()
		self.confirm = Button(frame, text = "     Export     ", command = tofile)
		self.confirm.pack(side = TOP, fill = BOTH, expand = YES)


	# data structures to hold our bookmark buttons
	bmarkrenamebuttons, bmarkdeletebuttons, bmarknotebuttons = {}, {}, {}

	# configure bookmarks: delete or rename
	def bmarkconfig(self):
		if not Application.bookmarked:
			messagebox.showinfo("Notice", "There are no bookmarks.")
			return
		# open up panel to do configuring at
		bmenu = Toplevel()
		bmenu.title("Configure Bookmarks"), bmenu.focus_set(), bmenu.grab_set()
		[bmenu.columnconfigure(i, weight = 1) for i in range(5)]
		frame = Frame(bmenu)
		frame.grid()
		Application.bmarkrenamebuttons.clear()
		Application.bmarkdeletebuttons.clear()
		Application.bmarknotebuttons.clear()

		# helper to delete a bookmark
		def deletebmark(label, row):
			start = self.bookmarks.index(label)
			self.bookmarks.delete(start, start + 1)
			[Application.bookmarked.remove(p) for p in Application.bookmarked if p[0] == label]
			[w.destroy() for w in frame.grid_slaves() if int(w.grid_info()["row"]) == row]
			bmenu.destroy() if not frame.winfo_children() else None

		# helper to edit a note
		def editnote(label, tag):
			menu = Toplevel()
			menu.title("Edit Note")
			menu.focus_set(), menu.grab_set()
			topframe, bottomframe = Frame(menu), Frame(menu)
			topframe.grid(row = 0, column = 0)
			bottomframe.grid(row = 1, column = 0)
			notebox = Text(topframe, wrap = NONE, height = 15, width = 80, font = ("Times, 8"))
			notebox.grid(row = 0, column = 0)

			def submitedit():
				newnote = notebox.get("0.0", END).strip()
				if newnote == "" or newnote.isspace():
					messagebox.showinfo("Note", "Note cannot be whitespace.")
					return
				index = 0
				for i in Application.bookmarked:
					if i[0] == label:
						break
					index += 1
				content = Application.bookmarked[index][1]
				Application.bookmarked[index] = label, content, newnote
				ix = self.bookmarks.index(label)
				self.bookmarks.entryconfigure(ix, command = lambda p1 = content, p2 = newnote: self.bmarkclick(p1, p2))
				menu.destroy()

			submitbutton = Button(bottomframe, text = "Submit Edit", command = submitedit)
			submitbutton.grid(row = 0, column = 0)
			
	
		# helper to rename a bookmark
		def renamebmark(entry, label, widget, tag):
			ix = self.bookmarks.index(label)
			rename = entry.get().strip()
			entry.delete(0, END)
			if rename.isspace() or rename == '':
				return
			elif rename.isdigit():
				messagebox.showinfo("Note", "Bookmark name cannot be a number.")
				return
			try:
				test = self.bookmarks.index(rename)
				messagebox.showinfo("Note", "There is already a bookmarked named " + rename)
				return
			# if this is a bad menu index, then it is unique so we can proceed
			except Exception:
				self.bookmarks.entryconfigure(ix, label = rename)
				widget["text"] = rename
				index = 0
				marks = Application.bookmarked
				for i in marks:
					if i[0] == label:
						break
					index += 1
				# update the bookmarks tuple
				marks[index] = rename, marks[index][1], marks[index][2]
				# change the button function bindings
				Application.bmarkrenamebuttons[tag].config(command = lambda p1 = entry, p2 = rename, \
					p3 = widget, p4 = tag: renamebmark(p1, p2, p3, p4))
				Application.bmarkdeletebuttons[tag].config(command = lambda p1 = rename, p2 = tag: \
					deletebmark(p1, p2))
				Application.bmarknotebuttons[tag].config(command = lambda p1 = rename, p2 = tag: \
					editnote(p1, p2))


		count = 0
		# dyamically create buttons on the menu for configuration options
		for mark in Application.bookmarked:
			labeltext = self.bookmarks.entrycget((count * 2) + 5, option = "label")
			widget = Label(frame, text = labeltext)
			widget.grid(row = count, column = 0)
			e = Entry(frame)
			e.grid(row = count, column = 1, padx = 3)
			Application.bmarkrenamebuttons[count] = Button(frame, text = "Rename", command = lambda p1 = e, \
				p2 = labeltext, p3 = widget, p4 = count: renamebmark(p1, p2, p3, p4))
			Application.bmarkrenamebuttons[count].grid(row = count, column = 2)
			Application.bmarkdeletebuttons[count] = Button(frame, text = "Delete", command = lambda p1 = labeltext, \
				p2 = count: deletebmark(p1, p2))
			Application.bmarkdeletebuttons[count].grid(row = count, column = 3)

			Application.bmarknotebuttons[count] = Button(frame, text = "Edit Note", command = lambda p1 = labeltext, \
				p2 = count: editnote(p1, p2))
			Application.bmarknotebuttons[count].grid(row = count, column = 4)
			count += 1


	# add bookmarks based on line #, label, and note
	def addbmark(self):
		if self.popupinst.filters != []:
			messagebox.showinfo("Note", "Can't add bookmarks when highlighted lines are filtered.")
			return
		elif self.popupinst.hidden:
			messagebox.showinfo("Note", "Can't add bookmarks when unhighlighted lines are filtered.")
			return

		# open up the entry panel
		menu = Toplevel()
		menu.title("Add a Bookmark")
		menu.focus_set(), menu.grab_set()
		topframe = Frame(menu)
		middleframe = Frame(menu)
		bottomframe = Frame(menu)

		# place the widgets on the frame
		topframe.pack(expand = YES, fill = BOTH, side = TOP)
		middleframe.pack(expand = YES, fill = BOTH, side = TOP)
		bottomframe.pack(expand = YES, fill = BOTH, side = TOP)
		entrylabel = Label(topframe, text = "Line #: ")
		entrylabel.pack(expand = YES, fill = BOTH, side = LEFT)
		lineentry = Entry(topframe)
		lineentry.pack(expand = YES, fill = BOTH, side = LEFT)
		namelabel = Label(topframe, text = "Bookmark Name:")
		namelabel.pack(expand = YES, fill = BOTH, side = LEFT)
		nameentry = Entry(topframe)
		nameentry.pack(expand = YES, fill = BOTH, side = LEFT)
		notebox = Text(middleframe, wrap = NONE, height = 15, width = 80, font = ("Times, 8"))
		notebox.pack(expand = YES, fill = BOTH)
		# helper function to save the bookmark
		def submitnote():
			linenum = lineentry.get().strip()
			if linenum == "" or linenum.isspace():
				messagebox.showinfo("Note", "Enter a line number.")
				return
			elif not linenum.isdigit():
				messagebox.showinfo("Note", "Must enter a number for line #.")
				return
			elif int(linenum) > len(Application.lines[1:]):
				messagebox.showinfo("Note", "Line number out of range")
				return
			label = nameentry.get().strip()
			if label == "" or label.isspace():
				messagebox.showinfo("Note", "Enter a bookmark name.")
				return
			elif label in [m[0] for m in Application.bookmarked]:
				messagebox.showinfo("Note", "Bookmark named '" + label + "' already exists.")
				return
			note = notebox.get("0.0", END).strip()
			if note == "" or note.isspace():
				messagebox.showinfo("Note", "Note cannot be whitespace.")
				return
			content = Application.lines[int(linenum)]
			# same line contents and note means we can't add the bookmark
			if (content, note) in [(i[1], i[2]) for i in Application.bookmarked]:
				messagebox.showinfo("Note", "Bookmark with this particular note already exists.")
				return
			info = (label, content, note)
			Application.bookmarked.append(info)
			self.bookmarks.add_command(label = label, command = \
				lambda p1 = content, p2 = note : self.bmarkclick(p1, p2))
			self.bookmarks.add_separator()
			menu.destroy()

		notebutton = Button(bottomframe, text = "Submit Note", command = submitnote)
		notebutton.pack(expand = YES, fill = BOTH)


	# prints out the file contents onto the main text box
	def printfile(self, file, filename):
		self.box.config(state = NORMAL)
		# delete all previous contents in textbox
		self.box.delete(0.0, END)
		# delete menu options
		self.bookmarks.delete(0, END)
		self.submenu.delete(11, END)
		# reset all class variables
		self.popupinst = Popup(self)
		Application.lines[:] = ['']
		Application.highlights = 0
		Application.keycolors.clear()
		Application.linetocolors.clear()
		Application.currentlines.clear()
		Application.text.clear()
		Application.colortolines.clear()
		Application.searchstrings[:] = []
		Application.bookmarked[:] = []
		Application.prevcolors.clear()
		Application.lastcolor[:] = []
		Application.jumpmenu = None
		Application.forwards, Application.backwards = False, False
		Application.nocaselst[:] = []

		# populate dictionary data structures with empty keys
		for color in Application.colors:
			Application.colortolines[color] = []
			Application.currentlines[color] = []
			Application.text[color] = None

		# determine # of files needed based on max # lines per file
		numlines = sum(1 for line in open(filename, "r"))
		lim = Application.splitlimit
		if numlines <= lim:
			numfiles = 0
		elif numlines % lim == 0:
			numfiles = numlines // lim
		else:
			numfiles = (numlines // lim) + 1
		filename = filename.replace(".log", "").replace(".txt", "")
		# create enough files necessary
		backups = [open("%s_%d.txt" % (filename, n), "w+") for n in range(1, numfiles + 1)]

		# generate popup message confirming file creation
		if backups:
			files = ""
			for i in backups:
				files += i.name + ", "
			messagebox.showinfo("Note", "File too large, it was split up into the following files:\n%s" \
				% files.strip().rstrip(","))
		self.master.title("Log Viewer | " + backups[0].name) if backups else None

		linenum, filenum = 1, 1
		for line in file:
			self.box.insert(INSERT, str(linenum).rjust(6) + "\t" + line) if linenum <= lim else None
			backups[filenum - 1].write(line) if backups else None
			if linenum % lim == 0:
				filenum += 1
			Application.lines.append(line)
			Application.linetocolors[linenum] = []
			linenum += 1
		file.close()
		[f.close() for f in backups]

		# remove unnecessary files that were not written to
		os.remove(backups[-1].name) if backups and os.path.getsize(backups[-1].name) == 0 else None
		# populate filterlines with all Trues for nowm indicating to not filter it
		self.popupinst.filterlines[:] = [True for i in Application.lines]
		self.box.config(state = DISABLED)
		# put some buttons into the top toolbar

		# add some stuff to the bookmarks menu
		self.submenu.add_command(label = "Export Matches to File", command = self.export)
		self.submenu.add_separator()

		# take all unfiltered lines on screen and export to a text file
		def saveas():
			f = filedialog.asksaveasfile(mode='w', defaultextension=".txt")
			contents = self.box.get("0.0", END).strip()
			if contents == "" or contents.isspace():
				messagebox.showinfo("Note", "There is no text to save.")
				return
			[f.write(line) for line in self.box.get("0.0", END)]
			fname = f.name
			f.close()
			f = open(fname, "r")
			lines = []
			[lines.append(line) for line in f]
			f.close()
			f = open(fname, "w")
			[f.write(re.search("(\t)(.*)", line).group(0).strip() + "\n") for line in lines if not line.isspace()]

		# saves any unfiltered text into a new file
		self.submenu.add_command(label = "Save As", command = saveas)
		self.submenu.add_separator()

		# some bookmark menu options
		self.bookmarks.add_separator()
		self.bookmarks.add_command(label = "Configure", command = self.bmarkconfig)
		self.bookmarks.add_separator()
		self.bookmarks.add_command(label = "Add Bookmark", command = self.addbmark)
		self.bookmarks.add_separator()

		# if the default file exists, prompt to load it or not
		defaultfile = os.path.join(os.getcwd(), "defaultsearchstrings.txt")
		if os.path.isfile(defaultfile):
			loadmenu = Toplevel()
			loadmenu.title("Confirmation: Load Default Search Strings")
			loadmenu.focus_set(), loadmenu.grab_set()
			frame = Frame(loadmenu)
			frame.pack(expand = YES, fill = BOTH)
			def action(yes = True):
				self.loadsearch(default = defaultfile, changedir = False) if yes else None
				loadmenu.destroy()
			Label(frame, text = "Load Default Search Strings?").pack(expand = YES, fill = BOTH)
			Button(frame, text = "Yes", command = action).pack(expand = YES, fill = BOTH)
			Button(frame, text = "No", command = lambda: action(yes = False)).pack(expand = YES, fill = BOTH)


		self.disablebutton.config(command = self.popupinst.createwindow)
		self.jumpbutton.config(command = self.jumpframe)


		# keyboard event to jump to a line
		def keyboardgo(event):
			self.goline()
			# bind it to the enter key
		self.bmarkentry.bind("<Return>", keyboardgo)
		self.bmarkgo.config(command = self.goline)


		# functions to move to bottom and top of the text box
		def top(event):
			self.box.see(str(float(0)))
		def bottom(event):
			self.box.see(str(float(len(Application.lines) - 1)))
		# bind these fucntions to the shift up and down key commands
		self.master.bind("<Up>", top), self.master.bind("<Down>", bottom)

	# data structures needed to deal with jumping logic
	prevcolors, lastcolor = {}, []
	for i in colors:
		prevcolors[i] = None
	jumpmenu = None
	forwards, backwards = False, False

	def exit(self, tag, color):
		self.box.tag_config(tag, background = color, foreground = "black")
		Application.jumpmenu.destroy()

	# helper function to do the actual jumping to certain lines
	def jump(self, color, label, strn, prev = False):

		lastcolor = Application.lastcolor
		prevcolors = Application.prevcolors
		recolor = None
		if lastcolor and prevcolors[lastcolor[0]] is not None:
			tag = prevcolors[lastcolor[0]][0]
			recolor = prevcolors[lastcolor[0]][1]
			self.box.tag_config(tag, background = recolor, foreground = "black")
		currs = Application.currentlines
		countvar = StringVar()
		currs[color].pop() if prev and currs[color] != [] else None
		if currs[color] == []:
			start = "0.0"
		else:
			start = currs[color][len(currs[color]) - 1]
		pos = self.box.search(strn, start, END, count = countvar)
		if not pos:
			countvar = StringVar()
			if strn.lower() in Application.nocaselst and re.search("\W+", strn):
				pos = self.box.search(strn, start, END, count = countvar, nocase = True, regexp = True)
			elif strn.lower() in Application.nocaselst:
				pos = self.box.search(strn, start, END, count = countvar, nocase = True)
			elif re.search("\W+", strn):
				pos = self.box.search(strn, start, END, count = countvar, regexp = True)
			else:
				pos = self.box.search(strn, "0.0", END, count = countvar)
		if pos:
			if prev:
				Application.backwards = True
			else:
				Application.forwards = True
			label["text"] = "\t" + str(int(float(pos))) + "\t"
			Application.text[color] = label["text"]
			currs[color].append(str(float(pos) + 1)) if not prev else None
			linepos = str(float(int(float(pos))))
			line = self.box.get(linepos, "%s.%s" % (int(float(linepos)), 100000))
			line = re.sub("^(\s*)[0-9]+(\s*)\t", "", line)
			newvar = StringVar()
			pos = self.box.search(line, linepos, END, count = newvar)
			tag = pos
			self.box.see(pos)
			self.box.tag_delete(tag) if tag in self.box.tag_names() else None 
			self.box.tag_add(tag, pos, "%s + %sc" % (pos, newvar.get()))
			self.box.tag_config(tag, background = "black", foreground = "white")	
			try:
				ix = Application.lines.index(line + "\n")
			except Exception:
				ix = 0
				one, two = line.lstrip(), line.lstrip() + "\n"
				for i in Application.lines:
					i = i.lstrip()
					if one == i or two == i:
						break
					ix += 1
			recolor = Application.linetocolors[ix][-1]
			prevcolors[color] = (tag, recolor)
			if len(lastcolor) == 0:
				lastcolor.append(color)
			else:
				lastcolor[0] = color
			if recolor is not None:
				newcolor = recolor
			else:
				newcolor = lastcolor[0]
			Application.jumpmenu.protocol("WM_DELETE_WINDOW", lambda p1 = tag, p2 = newcolor : self.exit(p1, p2))

			# perform another jump if we ever get stuck
			if Application.forwards and prev:
				Application.forwards = False
				self.jump(color, label, strn, prev = True)
			elif Application.backwards and not prev:
				Application.backwards = False
				self.jump(color, label, strn)

	
	# helper function for creating new frame for jump control buttons
	def jumpframe(self):
		if not self.popupinst.usedcolors:
			messagebox.showinfo("Notice", "Nothing is highlighted.")
			return
		# open up new menu with buttons to control jumping
		Application.jumpmenu = Toplevel()
		Application.jumpmenu.title("Jump to Matching Lines")
		Application.jumpmenu.focus_set(), Application.jumpmenu.grab_set()
		frame = Frame(Application.jumpmenu)
		frame.grid()
		count = 0

		for color in Application.colortolines:
		# skip filtered colors or colors that do not exist
			if not Application.colortolines[color] or color in self.popupinst.filters:
				continue
			if Application.text[color] is None or self.popupinst.justfiltered:
				countertext = "\t \t"
			else:
				countertext = "\t" + Application.text[color] + "\t"
			counter = Label(frame, text = countertext, bg = color)
			strtext = [i for i in self.keycolors.keys() if self.keycolors[i] == color][0]
			strname = Label(frame, text = strtext, bg = color)
			prev = Button(frame, text = "Previous", \
				command = lambda p1 = color, p2 = counter, p3 = strtext: self.jump(p1, p2, p3, prev = True))
			prev.grid(row = count, column = 0, sticky = W+E)
			counter.grid(row = count, column = 2, sticky = W+E+N+S)
			strname.grid(row = count, column = 1, sticky = W+E+N+S, padx = 5)
			nxt = Button(frame, text = "    Next    ", \
				command = lambda p1 = color, p2 = counter, p3 = strtext: self.jump(p1, p2, p3))
			nxt.grid(row = count, column = 3, sticky = W+E)
			count += 1

		Application.jumpmenu.destroy() if not frame.winfo_children() else None
		self.popupinst.justfiltered = False


	nocaselst = []

	# highlight lines matching a keyword or a regex
	def highlight(self, key = None, child = False, load = False, color = False):
		# get the keyword to search
		if key is None:
			if child:
				key = self.popupinst.keyentry.get()
				self.popupinst.keyentry.delete(0, END)
			else:
				key = self.keyentry.get()
				self.keyentry.delete(0, END)
		# ignore whitespace or if the keyword has already been highlighted
		if key == '' or key.isspace():
			messagebox.showinfo("Notice", "Key cannot be whitespace.")
			return
		elif key in Application.keycolors and not load:
		 	messagebox.showinfo("Notice", "Key is already highlighted.")
		 	return
		elif len(Application.lines) <= 1:
			messagebox.showinfo("Notice", "No file loaded onto display.")
			return
		ignore = False
		# handles case when we ignore case of the search
		if self.ignorecase.get() or (child and self.popupinst.ignorecase.get()):
			# when the lower case of this case has already been searched
			if key.lower() in [k.lower() for k in Application.keycolors]:
				messagebox.showinfo("Notice", "Case-ignored key is already highlighted.")
				return
			else:
				key = key.lower()
				Application.nocaselst.append(key)
			ignore = True
		elif key in Application.keycolors:
			messagebox.showinfo("Notice", "Search string '" + key +  "' already exists.")
			return
		# handles case when we only do the searching
		if self.searchonly.get() and not load:
			# ignore argument so we can decide whether or not to make lines lower case
			self.jumpsearch(key, ignore)
			return
		count, start = 1, 1
		# cycle through possible colors after each successful highlight
		if not color:
			color = self.colorselect()
		# iterate through all lines of file
		for line in Application.lines[1:]:
			# save the old line for search purposes
			oldline = line
			# if ignore case, convert the line to lower case
			if self.ignorecase.get() or (child and self.popupinst.ignorecase.get()):
				line = line.lower()
			# if either regex match or if the keyword is in the line
			if (self.regex.get() and re.search(key, line)) or key in line \
				or (child and self.popupinst.regex.get() and re.search(key, line)):
				Application.linetocolors[count].append(color)
				Application.colortolines[color].append(count)
				countvar = StringVar()
				if self.regex.get() and re.search(key, line):
					pos = self.box.search(oldline, str(float(start)), END, count = countvar, regexp = True)
				else:
					pos = self.box.search(oldline, str(float(start)), END, count = countvar)
				if pos:
					tag = oldline
					self.box.tag_delete(tag) if tag in self.box.tag_names() else None 
					self.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
					self.box.tag_config(tag, background = color)
					start = int(float(pos)) + 1
			count += 1
		# update some variables if we actually found matches
		if start != 1:
			Application.highlights += 1
			Application.keycolors[key] = color
			self.popupinst.usedcolors.append(color)
			Application.searchstrings.append(key)
			[[self.popupinst.popup.destroy(), self.popupinst.createwindow()] for i in range(1) if child]
		else:
			messagebox.showinfo("Notice", "Key does not exist")


# class for popup messages
class Popup:

	def __init__(self, parent):
		# the app that called me
		self.parent = parent

		# data structures to hold our buttons
		self.buttons = {}
		self.deletebuttons = {}
		self.colorbuttons = {}
		self.usedcolors = []
		self.filterbuttons = {}

		# color -> lines
		self.filtercolors = {}

		# line -> en or dis
		self.filterlines = []

		# colors that were filtered
		self.filters = []

		# whether or not we just filtered something
		self.justfiltered = False


		# mapping from color to a list of lines that need to be recolored that color
		self.disabledlines = {}

		# whether unhighlighted lines are hidden
		self.hidden = False


		# populate these data structures with empty keys
		for color in Application.colors:
			self.disabledlines[color] = []
			self.filtercolors[color] = []


	# creates window for buttons to control displayed highlights
	def createwindow(self):
		if not self.usedcolors:
			messagebox.showinfo("Notice", "Nothing is highlighted.")
			return
		self.buttons.clear(), self.deletebuttons.clear()
		self.colorbuttons.clear(), self.filterbuttons.clear()
		# the screen we use
		self.popup = Toplevel()
		self.popup.title("Configure Search Strings")
        # freezes root window and thus prevents additional popups
		self.popup.focus_set(), self.popup.grab_set()
		# divide the popup into columns
		# frame creation
		self.top = Frame(self.popup)
		self.left = Frame(self.popup)
		self.right = Frame(self.popup)
		self.far = Frame(self.popup)
		self.east = Frame(self.popup)
		self.bottom = Frame(self.popup)

		# load frames onto the grid
		self.top.grid(row = 0, column = 0, sticky = W+E+N+S)
		self.left.grid(row = 1, column = 0, sticky = W+E+N+S)
		self.right.grid(row = 1, column = 1, sticky = W+E+N+S)
		self.far.grid(row = 1, column = 2, sticky = W+E+N+S)
		self.east.grid(row = 1, column = 3, sticky = W+E+N+S)
		self.bottom.grid(row = 2, column = 0, sticky = W+E+N+S)

		# button to filter out all unhighlighted lines
		self.filterwhite = Button(self.bottom, text = "Hide Unhighlighted", command = lambda: self.hidewhite(self.hidden))
		self.filterwhite.config(text = "Show Unhighlighted") if self.hidden else None
		self.filterwhite.grid(row = 0, column = 0, padx = 15, pady = 5)

		# keyword search widgets
		self.keyword = Label(self.top, text = "Keyword: ")
		self.keyentry = Entry(self.top, width = 25)
		self.keyword.grid(row = 0, column = 1, padx = 0)
		self.keyentry.grid(row = 0, column = 2, padx = 0)
		self.keyentry.bind_class("Entry", "<Button-3><ButtonRelease-3>", copypaste)

		# bind highlight to the enter key for popup widget
		def keyboardhighlight(event):
			self.parent.highlight(child = True)
		self.keyentry.bind("<Return>", keyboardhighlight)
	
		self.keysearch = Button(self.top, text = "Search", command = lambda: self.parent.highlight(child = True))
		self.keysearch.grid(row = 0, column = 5, padx = 0, sticky = W+E)
		self.ignorecase = BooleanVar()
		self.entrycase = Checkbutton(self.top, text = "Ignore Case", variable = self.ignorecase)
		self.entrycase.grid(row = 0, column = 3, padx = 5)
		# regex checkbox for option to search regex instead of a keyword
		self.regex = BooleanVar()
		self.doregex = Checkbutton(self.top, text = "Regex", variable = self.regex)
		self.doregex.grid(row = 0, column = 4, padx = 5)
		# which row to place buttons in
		numrow = 0
		# dynamic button creation
		for string in self.parent.searchstrings[::-1]:
			strcolor = self.parent.keycolors[string]
			# the button to toggle the string
			self.buttons[string] = Button(self.left, \
				command = lambda param = string: self.toggle(param))
			# if disabled list is not empty, then that color is disabled...
			if self.disabledlines[strcolor] != []:
				self.buttons[string].config(bg = "white", text = "Show '" + string + "'")
			else:
				self.buttons[string].config(bg = strcolor, text = "Hide '" + string + "'")
			self.buttons[string].grid(row = numrow, column = 0, sticky = W+E, padx= 15)
			# the button to change string colors
			self.colorbuttons[string] = Button(self.left, text = "Change Color", \
				bg = strcolor, command = lambda param = string: self.colorconfig(param))
			self.colorbuttons[string].grid(row = numrow, column = 1, sticky = W+E, padx = 15)
			self.filterbuttons[string] = Button(self.left, text = "Filter Lines", \
				bg = strcolor, command = lambda param = string: self.filter(param))
			self.filterbuttons[string].grid(row = numrow, column = 2, sticky = W+E, padx = 15)
			# the button to delete strings
			self.deletebuttons[string] = Button(self.left, text = "Delete Highlight", \
				command = lambda param = string: self.delete(param))
			self.deletebuttons[string].grid(row = numrow, column = 3, sticky = W+E, padx = 15)
			if self.filtercolors[strcolor] != []:
				self.filterbuttons[string].config(text = "Unfilter Lines", bg = "white")
			numrow += 1

	# function to hide all unhighlighted text
	def hidewhite(self, hidden):
		if self.filters != []:
			messagebox.showinfo("Notice", "Unhighlighted lines can only be hidden/unhidden when no filters are applied.")
			return
		self.parent.box.config(state = NORMAL)
		self.parent.box.delete("0.0", END)
		coloredlines = []
		[[coloredlines.append(i) for i in self.parent.colortolines[j]] for j in self.parent.colortolines]
		count, start, linecount = 1, 1, 1
		for line in Application.lines[1:]:
			if hidden or count in coloredlines:
				lst = self.parent.linetocolors[count]
				if len(lst) == 0:
					recolor = "white"
				else:
					recolor = lst[len(lst) - 1]
				shownline = str(linecount).rjust(6) + "\t" + line
				self.parent.box.insert(INSERT, shownline)
				countvar = StringVar()
				pos = self.parent.box.search(line, str(float(start)), END, count = countvar)
				tag = line
				self.parent.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
				self.parent.box.tag_config(tag, background = recolor)
				start = int(float(pos)) + 1
				linecount += 1
			count += 1
		self.filterwhite.config(text = "Show Unhighlighted") if not self.hidden else \
			self.filterwhite.config(text = "Hide Unhighlighted")
		self.hidden = not self.hidden
		self.parent.box.config(state = DISABLED)
		self.justfiltered = True


	# filters out certain colored lines by removing them
	def filter(self, strn):
		color = self.parent.keycolors[strn]
		maxline = 0
		for i in self.parent.colortolines:
			lst = self.parent.colortolines[i]
			if lst and max(lst) > maxline:
				maxline = max(lst)
		if self.disabledlines[color]:
			messagebox.showinfo("Notice", "Color can only be filtered when the string is not hidden.")
			return
		elif self.hidden:
			messagebox.showinfo("Notice", "Color can only be filtered when unhighlighted lines are visible.")
			return
		self.parent.box.config(state = NORMAL)
		self.parent.box.delete("0.0", END)
		if self.filtercolors[color] == []:
			self.filters.append(color)
			self.filtercolors[color] = [i for i in self.parent.colortolines[color]]
			self.filterbuttons[strn].config(text = "Unfilter Lines", bg = "white")
			filt = True
		else:
			self.filters.remove(color)
			self.filterbuttons[strn].config(text = "Filter Lines", bg = color)
			filt = False
		count, linecount, start = 1, 1, 1
		for line in Application.lines[1:]:
			if count in self.filtercolors[color]:
				if filt:
					self.filterlines[count] = False
				else:
					self.filterlines[count] = True
			if self.filterlines[count]:
				shownline = str(linecount).rjust(6) + "\t" + line
				self.parent.box.insert(INSERT, shownline)
				linecount += 1
				lst = self.parent.linetocolors[count]
				if lst and count <= maxline:
					recolor = lst[len(lst) - 1]
					countvar = StringVar()
					pos = self.parent.box.search(line, str(float(start)), END, count = countvar)
					tag = line
					self.parent.box.tag_delete(tag) if tag in self.parent.box.tag_names() else None 
					self.parent.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
					self.parent.box.tag_config(tag, background = recolor)
					start = int(float(pos)) + 1
			count += 1
		self.filtercolors[color].clear() if not filt else None
		[Application.currentlines[i].clear() for i in Application.currentlines]
		for i in Application.text:
			Application.text[i] = None
		self.justfiltered = True
		self.parent.box.config(state = DISABLED)


	# helper function for creating window of all color option buttons
	def colorconfig(self, strn):
		# the color that we are changing
		currcolor = self.parent.keycolors[strn]
		# can only change colors when the string is not disabled
		if self.disabledlines[currcolor]:
			messagebox.showinfo("Notice", "Color can only be changed when the string is not hidden.")
			return
		elif self.filters != []:
			messagebox.showinfo("Notice", "Color can only be changed when no filters are applied.")
			return
		elif self.hidden:
			messagebox.showinfo("Notice", "Color can only be changed when unhighlighted lines are visible.")
			return
		colormenu = Toplevel()
		colormenu.title("Change color of lines matching keyword or regex: " + strn)
		# freezes bottom layers
		colormenu.focus_set(), colormenu.grab_set()
		frame = Frame(colormenu)
		frame.grid()
		colorlst = [c for c in Application.colors]
		# create grid of buttons
		for i in range(6):
			for j in range(6):
				color = colorlst.pop(0)
				if color not in self.usedcolors:
					button = Button(frame, text = color.upper(), bg = color, command = \
						lambda param = color: changecolor(param))
				else:
					button = Button(frame, text = "COLOR TAKEN", bg = "white")
				button.grid(row = i, column = j, sticky = W+E+N+S)

		# function that does the color changing
		def changecolor(newcolor):
			self.parent.keycolors[strn] = newcolor
			mappings = self.parent.linetocolors
			start = 0
			for linenum in mappings:
				lst = mappings[linenum]
				if currcolor in lst:
					ix = lst.index(currcolor)
					lst[ix] = newcolor
					self.parent.colortolines[currcolor].remove(linenum)
					self.parent.colortolines[newcolor].append(linenum)
					if self.disabledlines[currcolor] == []:
						if not lst:
							recolor = newcolor
						else:
							recolor = lst[len(lst) - 1]
						countvar = StringVar()
						searchline = Application.lines[linenum]
						pos = self.parent.box.search(searchline, str(float(start)), END, count = countvar)
						tag = searchline
						self.parent.box.tag_delete(tag) if tag in self.parent.box.tag_names() else None 
						self.parent.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
						self.parent.box.tag_config(tag, background = recolor)
						start = int(float(start)) + 1
			# if the current color is not disabled
			if self.disabledlines[currcolor] == []:
				self.buttons[strn].config(bg = newcolor, text = "Hide '" + strn + "'")
				self.colorbuttons[strn].config(bg = newcolor)
				self.filterbuttons[strn].config(bg = newcolor)
			repl = self.usedcolors.index(currcolor)
			self.usedcolors[repl] = newcolor
			colormenu.destroy()
			self.popup.focus_set()
			self.popup.grab_set()
			Application.currentlines[newcolor] = [i for i in Application.currentlines[currcolor]]
			Application.currentlines[currcolor][:] = []
			temp = Application.text[currcolor]
			Application.text[newcolor] = temp
			Application.text[currcolor] = None


	# hides or deletes highlights
	def hide(self, searchstr, deletion = False):
		color = self.parent.keycolors[searchstr]
		if deletion:
			self.buttons[searchstr].destroy()
			self.deletebuttons[searchstr].destroy()
			self.colorbuttons[searchstr].destroy()
			self.filterbuttons[searchstr].destroy()
			self.popup.destroy() if not self.left.winfo_children() else None
			self.parent.keycolors.pop(searchstr, None)
			self.parent.highlights -= 1
			self.usedcolors.remove(color)
			self.parent.searchstrings.remove(searchstr)
			Application.currentlines[color][:] = []
			Application.text[color] = None
		else:
			self.buttons[searchstr].config(bg = "white", text = "Show '" + searchstr + "'")
		mappings = self.parent.linetocolors
		start = 0
		for linenum in mappings:
			lst = mappings[linenum]
			if color in lst:
				lst.remove(color)
				self.parent.colortolines[color].remove(linenum)
				self.disabledlines[color].append(linenum) if not deletion else None
				if not lst:
					recolor = "white"
				else:
					recolor = lst[len(lst) - 1]
				countvar = StringVar()
				searchline = Application.lines[linenum]
				pos = self.parent.box.search(searchline, str(float(start)), END, count = countvar)
				tag = searchline
				self.parent.box.tag_delete(tag) if tag in self.parent.box.tag_names() else None 
				self.parent.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
				self.parent.box.tag_config(tag, background = recolor)
				start = int(float(pos)) + 1


	# shows all lines of a certain color
	def show(self, searchstr):
		color = self.parent.keycolors[searchstr]
		count = StringVar()
		self.buttons[searchstr].config(bg = color, text = "Hide '" + searchstr + "'")
		start = 0
		for linenum in self.disabledlines[color]:
			self.parent.linetocolors[linenum].append(color)
			countvar = StringVar()
			searchline = Application.lines[linenum]
			pos = self.parent.box.search(searchline, str(float(start)), END, count = countvar)
			tag = searchline
			self.parent.box.tag_delete(tag) if tag in self.parent.box.tag_names() else None 
			self.parent.box.tag_add(tag, pos, "%s + %sc" % (pos, countvar.get()))
			self.parent.box.tag_config(tag, background = color)
			self.parent.colortolines[color].append(linenum)
			start = int(float(pos)) + 1
		self.disabledlines[color].clear()


	# deletes all lines of a color
	def delete(self, strn):
		if self.filters != []:
			messagebox.showinfo("Notice", "Highlights can only be deleted when no filters are applied.")
			return
		elif self.hidden:
			messagebox.showinfo("Notice", "Highlights can only be deleted when unhighlighted lines are visible.")
			return
		color = self.parent.keycolors[strn]
		self.show(strn) if self.disabledlines[color] else None
		self.hide(strn, deletion = True)
		Application.nocaselst.remove(strn.lower()) if strn.lower() in Application.nocaselst else None


	# switches between hidden and shown
	def toggle(self, strn):
		if self.filters != []:
			messagebox.showinfo("Notice", "Highlights can only be toggled when no filters are applied.")
			return
		elif self.hidden:
			messagebox.showinfo("Notice", "Highlights can only be toggled when unhighlighted lines are visible.")
			return
		color = self.parent.keycolors[strn]
		self.show(strn) if self.disabledlines[color] else self.hide(strn)


app = Application(root)

# window size configuration depdendent on OS
if platform.system() == "Windows":
	root.wm_state("zoomed")
else:
	w, h = root.winfo_screenwidth(), root.winfo_screenheight()
	root.geometry("%dx%d+0+0" % (w, h))

root.mainloop()
