#!/bin/env python
import Tix
from Tkconstants import *
from orm import *
from forms import *
from gettext import gettext as _
from misc import *

class FieldEntry(object):
    
    def __init__(self, formeditor, parent, field, **kwargs):
        self.parent = parent
        self.formeditor = formeditor
        self.field = field
        self.form = self.formeditor.form
        self.variable = self.formeditor.form.tkvars[self.field.name]

    def disable(self):
        self.widget.config ( state='disabled' )
        
class TextEntry(FieldEntry):
    def __init__(self, *args, **kwargs):
        FieldEntry.__init__(self, *args, **kwargs)
        self.widget = Tix.Entry (self.parent, 
                                 width=self.formeditor.entrywidth, 
                                 disabledforeground="black",
                                 textvariable = self.variable)
        

class StaticEntry(FieldEntry):
    def __init__(self, *args, **kwargs):
        FieldEntry.__init__(self, *args, **kwargs)
        self.widget = Tix.Label (self.parent, 
                                 width=self.formeditor.entrywidth, 
                                 disabledforeground="black",
                                 textvariable = self.variable)    
        
class ReferenceEntry(FieldEntry):
    def __init__(self, *args, **kwargs):
        FieldEntry.__init__(self, *args, **kwargs)    
        self.value_change = conditionalmethod(self.value_change)        
        self.variable.trace ( 'w', self.value_change )
    
    def value_change(self, *args):
        pass
    
    
class StaticReferenceEntry(ReferenceEntry):    
    def __init__(self, *args, **kwargs):
        ReferenceEntry.__init__(self, *args, **kwargs)        
        self.display_variable = Tix.StringVar()
        self.widget = Tix.Label (self.parent, 
                                 width=self.formeditor.entrywidth,                                  
                                 textvariable = self.display_variable)
        

    def value_change(self, *args):
        self.display_variable.set ( getattr(self.formeditor.form.current, self.field.name + "_REF") )

class ComboReferenceEntry(ReferenceEntry):
    def __init__(self, *args, **kwargs):
        ReferenceEntry.__init__(self, *args, **kwargs)                
        self.cmb_command = conditionalmethod(self.cmb_command)

        reftable = self.field.reference        
        self.records = RecordList(reftable)
        self.records.reload()
        
        self.display_variable = Tix.StringVar()
        
        self.widget = Tix.ComboBox (self.parent, 
                                    editable=False, dropdown=True,
                                    options = "label.width 0 entry.width " + str(self.formeditor.entrywidth),                                     
                                    variable = self.display_variable,
                                    command=self.cmb_command)        
        self.entry = self.widget.subwidget ('entry')
        self.entry.config (disabledforeground="black")
        self.listbox = self.widget.subwidget('slistbox').subwidget('listbox')
        for r in self.records:
            self.widget.insert (Tix.END, r._astxt)
        self.widget.insert (Tix.END, "<no object>" )
        
        self.current = None        
    
    def cmb_command(self, *args):  
        
        #Was the call initiated by the ComboBox constructor?
        if not hasattr(self, 'listbox'): return        
        try:
            self.value_change.freeze()        
            idx, = self.listbox.curselection()
            self.current = self.records[int(idx)]
            self.variable.set (self.current.objectid)
        except IndexError:
            self.current = None
            self.variable.set (None)
            self.display_variable.set ( "<error> out of bounds" )
        finally:
            self.value_change.thaw()
    
    def value_change(self, *args):                
        """Handle a change in the field value initiated outside of 
        this editor"""                
        try:
            self.cmb_command.freeze()
            v = self.variable.get()
            self.current = None
            self.display_variable.set ( "" )
            if v is None or v == '': self.display_variable.set ( "<null> " )
            self.current = self.records.getid(int(v))
            self.display_variable.set ( self.current._astxt )
        except ValueError:
            pass            
        except KeyError:
            pass
        finally:
            self.cmb_command.thaw()
        
class BooleanEntry(FieldEntry):    
    def __init__(self, *args, **kwargs):
        FieldEntry.__init__(self, *args, **kwargs)
        self.display_variable = Tix.StringVar()        
        self.widget = Tix.Checkbutton ( self.parent, textvariable = self.display_variable, 
                                        variable = self.variable )
        self.variable.trace ( 'w', self.value_change )
    
    def value_change(self, *args):
        if self.variable.get() == '1':
            self.display_variable.set (_("YES"))
        else:
            self.display_variable.set (_("NO"))
            
###########################################################################################
class ArrayEntryTextMixin:    
    class ItemEditor(object):
        def __init__(self, arrayentry, idx):
            self.variable = Tix.StringVar()
            self.entry = Tix.Entry ( arrayentry.parent, textvariable=self.variable )
            self.tracecb = self.variable.trace ('w', partial(arrayentry.item_change, idx))
            self.entry.config ( width=arrayentry.formeditor.entrywidth )            
            arrayentry.editors.append (self)
            self.tracecb = None
            
        def destroy(self):
            if self.tracecb:
                self.variable.trace_vdelete ( 'w', self.tracecb )
            self.entry.forget()
            del self.entry, self.variable

class ArrayEntryButtonMixin:
    class ButtonBox(object):
        def __init__(self, arrentry,idx,_add=True,_del=True):
            self.frame = Tix.Frame ( arrentry.parent, width=arrentry.formeditor.commandwidth )
            if _add:
                self.bt_add = Tix.Button (self.frame, text='+', font=('Courier', 8, 'normal'), padx=0, pady=0, command=partial(arrentry.item_add, idx+1) )
                self.bt_add.pack(side=LEFT)
            if _del:
                self.bt_del = Tix.Button (self.frame, text='x', font=('Courier', 8, 'normal'), padx=0, pady=0, command=partial(arrentry.item_remove, idx) )            
                self.bt_del.pack(side=LEFT)
            if idx >= 0:
                arrentry.buttons.append (self)
        
        def destroy(self):
            self.frame.forget()
            del self.bt_add, self.bt_del, self.frame

class ArrayEntryComboMixin:
    class ItemEditor(object):
        def __init__(self, arrayentry, arrayidx):
            self.variable = Tix.StringVar()
            self.display_variable = Tix.StringVar()
            self.combo_selection = conditionalmethod(self.combo_selection)
            self.external_change = conditionalmethod(self.external_change)
            self.entry = Tix.ComboBox ( arrayentry.parent, 
                                        editable=False, dropdown=True,
                                        options = "label.width 0 entry.width " + str(arrayentry.formeditor.entrywidth),                                     
                                        variable=self.display_variable,
                                        command=self.combo_selection
                                        )
            self.listbox = self.entry.subwidget('slistbox').subwidget('listbox') 
            self.textbox = self.entry.subwidget('entry')
            self.textbox.config ( disabledforeground = "black" )
            self.value_idx = []
            self.disp_idx = []
            if arrayentry.choices:                
                for idx, (varval, dispval) in enumerate(arrayentry.choices):
                    self.value_idx.append(varval)
                    self.disp_idx.append (dispval)
                    self.entry.insert ( Tix.END, dispval )
            self.tracecb = self.variable.trace ('w', partial(arrayentry.item_change, arrayidx))
            self.localtrace = self.variable.trace ('w', self.external_change)
            arrayentry.editors.append (self)
            
        def external_change (self, *args):
            try:
                self.combo_selection.freeze()
                self.external_change.freeze()
                self.display_variable.set ( self.disp_idx[int(self.variable.get())] )
            except IndexError:
                self.display_variable.set ( self.variable.get() + " <no text>" )
            finally:
                self.external_change.thaw()
                self.combo_selection.thaw()
            
        def combo_selection(self, *args):
            print args
            idx, = self.listbox.curselection()
            self.combo_selection.freeze()
            self.variable.set ( self.value_idx[int(idx)] )            
            self.combo_selection.thaw()
            
        def destroy(self):        
            self.variable.trace_vdelete ( 'w', self.tracecb )        
            self.variable.trace_vdelete ( 'w', self.localtrace)
            self.entry.forget()
            del self.entry, self.variable
    
class ArrayEntryLabelMixin:
    class ItemEditor(object):        
        def __init__(self, arrayentry, idx):
            self.variable = Tix.StringVar()
            self.entry = Tix.Label ( arrayentry.parent, textvariable=self.variable )
        def destroy(self):
            del self.entry
            del self.variable
            
class ArrayEntry(FieldEntry):                
    def __init__(self, *args, **kwargs):
        FieldEntry.__init__(self, *args, **kwargs)
        self.value_change = conditionalmethod(self.value_change)        
        self.item_change = conditionalmethod(self.item_change)        
        self.branch = kwargs.get ( "branch", None )        
        self.recordlist = kwargs.get ("recordlist", None )
        self.choices = kwargs.get ("choices", None )
        
        self.widget = Tix.Label (self.parent, 
                                 width=self.formeditor.entrywidth, 
                                 textvariable = self.variable)
        if hasattr(self, "ButtonBox"):
            self.default_buttons = self.ButtonBox (self, -1, _del=False)
            self.parent.item_create ( self.field.name, 3, itemtype = Tix.WINDOW, window=self.default_buttons.frame )
        
        self.buttons = []
        self.array = []
        self.editors = []
        
        self.variable.trace ( 'w', self.value_change )

    def redisplay_array(self, newarray):
        print newarray
        if self.branch:                                
            for idx, val in enumerate(self.array):
                self.parent.delete_offsprings (self.field.name)
            for c in self.editors + self.buttons:
                c.destroy()
    
            self.buttons = []
            self.editors = []
            
            for idx, val in enumerate(newarray):
                                                
                self.parent.add (self.field.name+"/" + str(idx), itemtype=Tix.TEXT, text="+")                                        
                
                if hasattr(self, "ItemEditor"):
                    it = self.ItemEditor (self, idx )                                        
                    self.parent.item_create ( self.field.name+"/" + str(idx), 2, itemtype = Tix.WINDOW, window=it.entry )

                if hasattr(self, "ButtonBox"):
                    bb = self.ButtonBox(self, idx)                    
                    self.parent.item_create ( self.field.name+"/" + str(idx), 3, itemtype = Tix.WINDOW, window=bb.frame )
                
                it.variable.set ( val )
            self.array = newarray
        
    def value_change(self, *args):
        try:
            self.item_change.freeze()            
            self.redisplay_array(self.field.val_txt2py ( self.variable.get() ) or [])
        finally:
            self.item_change.thaw()

    
    def item_change(self, idx, *args):
        try:
            self.value_change.freeze()
            arr = map (lambda e: e.variable.get(), self.editors)            
            self.variable.set ( self.field.val_py2txt ( arr ) )
            self.array = arr
        finally:
            self.value_change.thaw()
        
    def item_add (self, atidx, *args):            
        self.array.insert (atidx, ' ')
        self.item_change.freeze()
        self.variable.set (self.field.val_py2txt (self.array))
        self.item_change.thaw()
        
    
    def item_remove (self, idx, *args):
        del self.array[idx]
        self.item_change.freeze()
        self.variable.set (self.field.val_py2txt (self.array))
        self.item_change.thaw()
        
        
class ArrayTextEntry(ArrayEntry, ArrayEntryTextMixin, ArrayEntryButtonMixin):
    pass


class ArrayReadOnlyEntry(ArrayEntry, ArrayEntryLabelMixin):
    pass


class ArrayComboEntry(ArrayEntry, ArrayEntryComboMixin, ArrayEntryButtonMixin):
    pass
###########################################################################################
class GenericFormEditor(object):    
    """ 
    ==GenericFormEditor==
    """
    __defaults__ = [ 
        ( "labelwidth", 20 ),
        ( "entrywidth", 40 ),
        ( "commandwidth", 10),
        ( "excludefields", []),
        ( "disablefields", []),
        ( "shownavigator", False),
        ( "showbuttons", True),
        ( "buttons", ["save", "reload", "new"] ),
    ]
    _button_label_ = {
        "save" : ( _("Save"), None),
        "reload" : ( _("Reload"), None),
        "new" : ( _("New"), None)
    }
    def __init__(self, parent, form, *args, **kwargs):
        for (attrname, defval) in self.__defaults__:
            self.__dict__[attrname] = kwargs.get ( attrname, defval )
            
        self.parent = parent
        self.create_toplevel()
        self.pack = self.toplevel.pack
        self.place = self.toplevel.place

        
        self.form = form
        self.editor_widgets = {}

        self.create_form_container()        
        self.build_form()
    
    def create_toplevel(self):
        self.toplevel = Tix.Frame (self.parent)
        

    def create_form_container(self):
        scrolled = Tix.ScrolledHList (self.toplevel, options="hlist.columns 4")

        self.hlist = scrolled.subwidget('hlist')
        self.hlist.configure ( separator="/",
                               background="white", foreground="black",
                               selectbackground="white", selectforeground="black")
        
      
        scrolled.pack(side=TOP, fill=BOTH, expand=1)
        scrolled.propagate(0)
        
        self.create_button_box()
        
        self.hlist.column_width(0, chars=1)
        self.hlist.column_width(1, chars=self.labelwidth)
        self.hlist.column_width(2, chars=self.entrywidth)
        self.hlist.column_width(3, chars=self.commandwidth)
    
    def create_button_box(self):
        if self.showbuttons:
            self.buttonbox = Tix.ButtonBox(self.toplevel, pady=0)
            for b in self.buttons: self.add_button(b)
            self.buttonbox.pack (side=BOTTOM, anchor=W )        
        
    def build_form(self):
        for f in self.form.table:            
            if (f.name in Table.__special_columns__ 
                or f.name in self.excludefields): continue           
            form_element = self.create_form_element(f)
            self.set_label ( form_element, self.create_label(f) )
            self.set_entry ( form_element, self.create_entry(f) )

    def create_form_element(self, field):
        self.hlist.add ( field.name, itemtype=Tix.TEXT, text=" " )
        return field.name
            
    def create_label(self, field):
        return field.label

    def set_label(self, form_element, label):
        self.hlist.item_create ( form_element, 1, itemtype=Tix.TEXT, text=label)

    def create_entry(self, field):
        try:
            return getattr(self, "_create_entry_" + field.name)(field)
        except AttributeError:
            pass
            
        var = self.form.tkvars[field.name]
        if field.isarray:
            entry = ArrayComboEntry(self, self.hlist, field, branch="array_" + field.name)
        elif field.reference:
            if field.editor_class == "StaticReferenceEntry":
                entry = StaticReferenceEntry ( self, self.hlist, field )
            else:
                entry = ComboReferenceEntry ( self, self.hlist, field )
        elif field.type == "bit":
            entry = BooleanEntry (self, self.hlist, field)
        else:
            entry = TextEntry ( self, self.hlist, field )
            
        self.editor_widgets[field.name] = entry
        if field.name in self.disablefields: entry.disable()
        
        return entry
    
    def set_entry(self, form_element, entry):
        self.hlist.item_create ( form_element, 2, itemtype=Tix.WINDOW, window=entry.widget )
        
    def button_command(self, buttonname, *args):                
        if hasattr(self, "handle_button_" + buttonname):
            getattr(self, "handle_button_" + buttonname)(*args)
            
    def handle_button_save(self, *args):
        self.form.save()

    def handle_button_reload(self, *args):
        self.form.reload()
            
    def add_button(self, buttonname, **kwargs):
        self.buttonbox.add ( buttonname, text=buttonname, command=lambda *x: self.button_command(buttonname, *x) )
    
###########################################################################################
class RecordPager(object):
    def __init__(self, *args, **kwargs):
        #kwargs: query, table, pagesize, idlist
        self.records = []
        self.records_hash = {}
        self.total_record_count = -1
        self.current_page = -1
        
    def getrecordbyid(self, objectid): return self.records_hash[objectid]
    def setobjectids(self, objids): pass
    def setrecords(self, records): pass
    def setpage(self, idx): pass
    def moverel(self, moveby): pass
    def next(self): pass
    def prev(self): pass
    def first(self): pass
    def last(self): pass
    def refresh(self): pass
    def __iter__(self): pass
    
class AbstractRecordListWidget(eventemitter):
    def __init__(self, *args, **kwargs):
        eventemitter.__init__ (self, [ 
            "current_record_changed", 
            "record_deleted",
            "navigate"
        ])
        
        self.records = []
        self.records_hash = {}
        
        self.parentform = kwargs.get ( "parentform", None )
        self.referencefield = kwargs.get ( "referencefield", None )        
        
        self.objecttype = kwargs.get ( "objecttype", "object" )
        self.allowsubclasses = kwargs.get ( "allowsubclasses", True )
        
        self.pager = kwargs.get ( "pager", None )
        self.records = kwargs.get ( "records", None )

        self.emitonbrowse = kwargs.get ( "emitonbrowse", True )
        self.recordtoolbox = kwargs.get ( "recordtoolbox", True )
        self.recordpopup = kwargs.get ( "recordpopup", True )        
        
        self.filterfunc = kwargs.get ( "filterfunc", lambda x: True )
        
        if self.parentform:
            self.parent_change_hook = self.parentform.register_event_hook ( "current_record_changed", self.parent_form_record_changed )
            
    def refreshDisplay(self):
        pass
        
    def setObjectIDs(self, objids):
        if self.pager:
            self.pager.setobjectids (objids)
            self.refreshDisplay()
        else:            
            self.setRecords ( [Record.ID (i) for i in objids] )
            
    def setRecords(self, recordlist):
        if self.pager:
            self.pager.setrecords (recordlist)
        else:
            self.records = recordlist
            self.records_hash.clear()
            for r in self.records: self.records_hash[r.objectid] = r
        self.refreshDisplay()
    
    def getRecordById (self, objid):
        if self.pager:
            return self.pager.getrecordbyid (objid)
        else:
            return self.records_hash[objid]

    def update(self):
        if self.parentform:
            self.setObjectIDs ( Record.IDLIST ( self.objecttype, where = [ self.referencefield + ' = ' + self.parentform.current.objectid ] ) )        

    def parent_form_record_changed(self, parentrecord, *args, **kwargs):        
        self.update()
        
class RecordListWidget(AbstractRecordListWidget):
    def __init__(self, parent, *args, **kwargs):
        AbstractRecordListWidget.__init__(self, *args, **kwargs)
        self.widget = Tix.ScrolledHList (parent, options="hlist.columns 4")
                                         
        self.hlist = self.widget.subwidget('hlist')
        self.hlist.config ( selectforeground="black", command = self.command_handler)
        if self.emitonbrowse:
            self.hlist.config ( browsecmd = self.command_handler)
        self.pack = self.widget.pack
        self.current_selected_record = None            
        
    def append_list_item(self, r):
        self.hlist.add ( r.objectid, itemtype=Tix.TEXT, text=str(r.objectid) )            
        self.hlist.item_create ( r.objectid, 1, itemtype=Tix.TEXT, text=r._astxt )
    
    def append_list_item_table_info(self, r):
        self.hlist.add ( r.objectid, itemtype=Tix.TEXT, text=str(r.objectid) )            
        self.hlist.item_create ( r.objectid, 1, itemtype=Tix.TEXT, text=r.name)

    def append_list_item_field_info(self, r):
        self.hlist.add ( r.objectid, itemtype=Tix.TEXT, text=str(r.objectid) )            
        self.hlist.item_create ( r.objectid, 1, itemtype=Tix.TEXT, text=r.name)
        self.hlist.item_create ( r.objectid, 2, itemtype=Tix.TEXT, text=r.type)
        
    def refreshDisplay(self):
        self.hlist.delete_all()        
        for r in self.records:
            try:
                getattr(self, "append_list_item_" + r.objecttype)(r)
            except AttributeError:
                self.append_list_item ( r )
    
    def command_handler(self, idx, *args):        
        if self.current_selected_record != idx:
            self.current_selected_record = idx
            record = self.getRecordById (int(idx))
            self.emit_event ( "current_record_changed", record )
            self.emit_event ( "navigate", record.objectid )
        
###########################################################################################
class MetadataEditorApp:    
    resource_dir = '/home/kuba/src/docsis-resources/'
    def __init__(self):
        self._root = Tix.Tk()
        
        self.rootwindow = Tix.Frame(self._root)

        wm = self._root.winfo_toplevel()        
        wm.title ( "Provisioning meta-data editor" )
        wm.geometry ( "1024x768+10+10" )
        
        self.rootwindow.pack(expand=1, fill=BOTH)
        self.rootwindow.propagate(0)
                
        self.table_list_frame = Tix.LabelFrame(self.rootwindow, label="Table list")
        self.table_list_frame.place ( relx=0, rely=0, relwidth=0.5, relheight=0.5)
        self.table_list_frame.propagate(0)

        self.table_record_list = RecordListWidget(self.table_list_frame)        
        self.table_record_list.pack(expand=1, fill=BOTH)
        self.table_record_list.setObjectIDs ( Record.IDLIST ( "table_info", order=["name"] ) )
        self.table_change_hook = self.table_record_list.register_event_hook ( "current_record_changed", self.table_changed )
            
        
        self.table_properties_frame = Tix.LabelFrame (self.rootwindow, label="Table properties" )
        self.table_properties_frame.place (relx=0.50, rely=0, relwidth=0.5, relheight=0.5)
        self.table_properties_frame.propagate(0)
        self.table_properties_form = Form ( Table.Get ( "table_info" ) )        
        self.table_properties = GenericFormEditor (self.table_properties_frame, 
                                                   self.table_properties_form,
                                                   disablefields = ["name", "schema"] )
        
        self.table_properties.pack(fill=BOTH, expand=1,padx=7, pady=20)
        
        self.field_list_frame = Tix.LabelFrame(self.rootwindow, label="Fields")
        self.field_list_frame.place ( relx=0, rely=0.51, relwidth=0.4, relheight=0.45)
        self.field_list_frame.propagate(0)
        
        self.field_record_list = RecordListWidget (self.field_list_frame, 
                                                   parentform=self.table_properties_form,
                                                   referencefield = "classid",
                                                   objecttype = "field_info" )
        self.field_record_list.pack (expand=1, fill=BOTH)
        self.field_change_hook = self.field_record_list.register_event_hook ( "current_record_changed", self.field_change )
        
        
        #scrolled = Tix.ScrolledTList(self.field_list_frame, scrollbars='y')
        #self.field_list = scrolled.subwidget('tlist')
        #self.field_list.configure (selectmode="single",
        #                           bg='white', selectbackground="blue",
        #                           selectforeground="white", orient='vertical',                                   
        #                           command=self.field_change_handler )
        #self.field_items = {}
        #scrolled.pack (expand=1, fill=BOTH, padx=7, pady=20)
        
        self.field_properties_frame = Tix.LabelFrame (self.rootwindow, label="Field properties" )
        self.field_properties_frame.place (relx=0.40, rely=0.51, relwidth=0.6, relheight=0.45)
        self.field_properties_frame.propagate(0)
        self.field_properties_form = Form ( Table.Get ( "field_info" ) )
        self.field_properties = GenericFormEditor (self.field_properties_frame,
                                                   self.field_properties_form ,
                                                   disablefields = [ "name", "type"],
                                                   excludefields = [ "path", "ndims" ]
                                                   )
        self.field_properties.pack (fill=BOTH, expand=1,padx=7, pady=20)
        
        #self.normal_field_style = Tix.DisplayStyle ( Tix.IMAGETEXT, refwindow=self.field_list, font = ("Helvetica", 11, "bold" ), foreground="black", bg='white' )
        #self.special_field_style = Tix.DisplayStyle ( Tix.IMAGETEXT, refwindow=self.field_list, font = ("Helvetica", 11, "italic" ), foreground="grey", bg='white' )        
        self._root.mainloop()        
                
    def table_change_handler(self, idx):
        table = self.table_items[int(idx)] 
        
    def table_changed(self,table_record,*args,**kwargs):
        table = Table.Get ( table_record.name )
        
        #for m in self.field_items:
        #    self.field_list.delete(m)
        #self.field_items.clear()

        #for idx, f in enumerate(table):
        #    if f.name in Table.__special_columns__: style = self.special_field_style
        #    else: style = self.normal_field_style
        #    self.field_list.insert (END, itemtype="imagetext", text=str(f),style=style) 
        #    self.field_items[idx] = f
        
        self.table_properties_form.setid ( table.id )
        self.table_properties_frame.configure ( label = self.table_properties_form.current._astxt ) 
        
    def field_change(self, field_record,*args, **kwargs):
        self.field_properties_form.setid ( field_record.objectid )
        self.field_properties_frame.configure ( label = self.field_properties_form.current._astxt )        
        
    def field_change_handler(self, idx):
        field = self.field_items[int(idx)]
        self.field_properties_form.setid ( field.id )
        self.field_properties_frame.configure ( label = self.field_properties_form.current._astxt )
        
###########################################################################################
abw = AbstractRecordListWidget()
abw.setObjectIDs ( Record.IDLIST ( "object", limit=10 ) )
#raise SystemExit
MetadataEditorApp()
