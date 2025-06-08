class GlobalObjects():
    def __init__(self, *args, **kwargs) :
        self.objects = dict()

    ## VALIDATION METHODS
    def validate_key(self, key) :
        if key == None :
            raise ValueError('Key missing!!')

        if not isinstance(key, str) :
            raise ValueError('Key not valid!!')

        return True

    def validate_value(self, value) :
        if value == None :
            raise ValueError('Value missing!!')

        return True
    
    def key_not_existance(self, key) :
        if key in self.objects :
            return False
        return True

    def validate(self, key, value) :
        if self.validate_key(key) and self.validate_value(value) and self.key_not_existance(key):
            return (key.lower(), value)
    ## END OF VALIDATION METHODS

    ## MAIN METHODS
    def add(self, key, value) :
        key, value = self.validate(key, value)
        
        self.objects[key] = value

    def obtain(self, key) :

        if self.validate_key(key) :
            return self.objects[key.lower()]


glob = GlobalObjects()