# Makes dictionaries dottable with keys:
# Instead of dict['key] you then use dict.key

class DotDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def dateToEnglish(date, date_format):
    date_string = str(date)
    months =  [
        'January', 'February', 'March', 
        'April', 'May', 'June', 'July', 
        'August', 'September', 'October', 
        'November', 'December'
        ]
    if date_format == "yyyy-mm-dd":
        year = date_string[0:4]
        month = int(date_string[5:7]) - 1
        day = date_string[8:10]
        if day == "1":
            day += "st"
        elif day == "2":
            day += "nd"
        elif day == "3":
            day+= "rd"
        else:
            day += "th"
        
        return day + " of " + months[month] + " " + year
    return "Unknown Date"