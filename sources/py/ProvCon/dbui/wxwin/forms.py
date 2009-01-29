##$Id$
from ProvCon.dbui.abstractui.forms import BaseForm
from ProvCon.dbui.orm import RecordList
from ProvCon.dbui.meta import Table
from fields import Entry as EntryWidgets
import wx

__revision__ = "$Revision$"


class GenericForm(BaseForm, wx.Panel):
    
    def __init__(self, form, parent, *args, **kwargs):
        BaseForm.__init__( self, form, *args, **kwargs )
        wx.Panel.__init__( self, parent, style=wx.TAB_TRAVERSAL)                
        
    def _build_ui(self):
        self.sizer = wx.FlexGridSizer( self.form.table.fieldCount() + 1, 3, 1, 0 )                                
        self.sizer.AddGrowableCol (1)
        for f in filter(lambda f: f.name not in Table.__special_columns__, self.form.table):
            label = wx.StaticText ( self, label = f.label )                        
            self.sizer.Add ( label, flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=20 )
            self.sizer.Add ( self._create_field_editor (f, self), 20, flag=wx.EXPAND)
            self.sizer.AddSpacer ( 20 )
        self.SetSizer (self.sizer)
        self.SetAutoLayout(1)
        
        #self.Bind ( wx.EVT_SIZE, self.resize )

    def resize(self, e):
        e.Skip()
                
    def _create_default_field_editor (self, field, parent=None, **kwargs):
        from app import APP
        editor_class_name = field.editor_class
        default_class = EntryWidgets.Text
        options = {}
        prefix = ''
        suffix = ''
        if field.isarray:
            if field.arrayof:
                editor_class_name = "Combo"
                prefix = "Array"
                options['recordlist'] = RecordList ( field.arrayof ).reload()           
                default_class = EntryWidgets.ArrayCombo
            else:
                prefix = 'Array'
                default_class = EntryWidgets.ArrayText
        elif field.reference:
            suffix = 'Reference'
            default_class = EntryWidgets.ComboReference
            
        print field, field.editor_class, editor_class_name
        
        if hasattr (EntryWidgets, prefix + editor_class_name + suffix):
            editor_class = getattr(EntryWidgets, editor_class_name)
        elif APP.getExtraDataEditor (prefix + editor_class_name + suffix):
            editor_class = APP.getExtraDataEditor (prefix + editor_class_name + suffix)
        else:
            editor_class = default_class
            
        editor = editor_class (field, parent, variable = self.form.getvar(field.name), **options )        
        return editor

class ScrolledGenericForm(wx.ScrolledWindow):
    
    def __init__(self, form, parent, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent)
        
        self.genericform = GenericForm(form, self, *args, **kwargs)
        self.genericform.create_widget()
        self.sizer = wx.BoxSizer()        
        self.sizer.Add ( self.genericform, flag=wx.EXPAND)
        self.SetSizer (self.sizer)
        self.SetScrollbars(20,20,50,50)        
        
        self.Bind ( wx.EVT_SIZE, self.on_resize)        
        self.genericform.Bind ( wx.EVT_SIZE, self.on_editor_resize )

    def on_editor_resize(self, event, *args):
        self.SetVirtualSize ( event.GetSize() )        
        event.Skip()
        
    def on_resize(self, event, *args):
        w, h = self.GetSize()        
        ew, eh = self.genericform.GetSize()
        self.genericform.SetMinSize ( ( w-20, eh ) )        
        self.genericform.SetVirtualSize ( (ew, eh) )
        event.Skip() 