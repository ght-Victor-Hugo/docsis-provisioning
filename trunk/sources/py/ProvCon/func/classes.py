
class conditionalmethod:
    def __init__(self, method):
        self.frozen = False
        self.method = method               
    def __call__(self, *args, **kwargs):        
        if self.frozen: return None        
        return self.method ( *args, **kwargs )
    def freeze (self):
        self.frozen = True        
    def thaw(self):
        self.frozen = False