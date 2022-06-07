import sys
sys.path.append('..')

from datetime import datetime, timedelta
from itertools import product

holiday_dict = {

        2013: ['-01-01', '-02-11', '-02-12', '-02-13', '-03-29', '-04-01', '-04-04', '-05-01', '-05-17', '-06-12',
               '-07-01', '-09-20', '-10-01', '-10-14', '-12-25', '-12-26'],

        2014: ['-01-01', '-01-31', '-02-03', '-04-05', '-04-18', '-04-21', '-05-01', '-05-06', '-06-02', '-07-01',
               '-09-09', '-10-01', '-10-02'  '-12-25', '-12-26'],

        2015: ['-01-01', '-02-19', '-02-20', '-04-03', '-04-06', '-04-07', '-05-01', '-05-25', '-07-01', '-09-03',
               '-09-28', '-10-01', '-10-21'  '-12-25'],

        2016: ['-01-01', '-02-08', '-02-09', '-02-10', '-03-25', '-03-28', '-04-04', '-05-02', '-06-09', '-07-01',
               '-09-16', '-10-10', '-12-26', '-12-27'],

        2017: ['-01-02', '-01-30', '-01-31', '-04-04', '-04-14', '-04-17', '-05-01', '-05-03', '-05-30', '-10-02', 
               '-10-05', '-12-25', '-12-26'],
    
        2018: ['-01-01', '-02-16', '-02-19', '-03-30', '-04-02', '-04-05', '-05-01', '-05-22', '-06-18', '-07-02', 
               '-09-25', '-10-01', '-10-17', '-12-25', '-12-26'],
    
        2019: ['-01-01', '-02-05', '-02-06', '-02-07', '-04-05', '-04-19', '-04-22', '-05-01', '-05-13', '-06-07', 
               '-07-01', '-10-01', '-10-07', '-12-25', '-12-26'],
    
        2020: ['-01-01', '-01-27', '-01-28', '-04-10', '-04-13', '-04-30', '-05-01', '-06-25', '-07-01', '-10-01', 
               '-10-02', '-10-13', '-10-26', '-12-25'],
    
        2021: ['-01-01', '-02-12', '-02-15', '-04-02', '-04-05', '-04-06', '-05-01', '-05-19', '-06-14', '-07-01',
               '-09-22', '-10-01', '-10-13', '-10-14', '-12-27'],

        2022: ['-02-01', '-02-02', '-02-03', '-04-05', '-04-15', '-04-18', '-05-02', '-05-09', '-06-03', '-07-01',
               '-09-12', '-10-04', '-12-26', '-12-27'],

        2023: ['-01-02', '-01-23', '-01-24', '-01-25', '-04-05', '04-07', '-04-10', '05-01', '05-26', '06-22',
               '-10-02', '-10-23', '-12-25', '12-26']

}
holiday_dict = {year: ['%s%s'%(str(year), dtstr) for dtstr in vallist] for year, vallist in holiday_dict.items()}

def get_workday_year(year, form):
    """Get all dates  to string in format 0 ('yyyy-mm-dd') or 1 ('yyyymmdd'') or 2 ('yymmdd)."""
    assert (form in [0, 1, 2]), 'Inappropriate form!'
    list_dtstr = []
    latest_date = datetime.strptime(str(year) + '-01-01', '%Y-%m-%d')
    while latest_date.year == year:
        if latest_date.weekday() <= 4:
            latest_dtstr = latest_date.strftime('%Y-%m-%d')
            if form == 0:
                list_dtstr.append(latest_dtstr)
            elif form == 1:
                list_dtstr.append(latest_dtstr.replace("-", ""))
            elif form == 2:
                list_dtstr.append(latest_dtstr.replace("-", "")[2:])
        latest_date += timedelta(days=1)
    return list_dtstr

def get_hkexday_year(year, form=0):
    """Get all HKEX trading day in a year."""
    list_dtstr = get_workday_year(year, form)
    holiday_list = holiday_dict[year]
    if form == 1:
        holiday_list = [name.replace("-", "") for name in holiday_list]
    elif form == 2:
        holiday_list = [name.replace("-", "")[2:] for name in holiday_list]
    for date in holiday_list:
        if date in list_dtstr:
            list_dtstr.remove(date)
    return list_dtstr

def getsetdate(monthstr='JAN-21'):
    """Obtain HK settlement date in a month."""
    monthstr = monthstr.capitalize()
    monthstr = '20%s-%s'%(monthstr[-2:], monthstr[:3])
    testdate = datetime.strptime(monthstr, '%Y-%b')
    yearwdaylist = get_hkexday_year(testdate.year, 0)
    mthdaylist = [testdate]
    while testdate.month == (testdate + timedelta(days=1)).month:
        testdate += timedelta(days=1)
        mthdaylist.append(testdate)
    mthdaylist = [date.strftime('%Y-%m-%d') for date in mthdaylist]
    mthdaylist = [dtstr for dtstr in mthdaylist if dtstr in yearwdaylist]
    setdate = datetime.strptime(mthdaylist[-2], '%Y-%m-%d')
    return setdate

## Settlement Day Dictionary
setdatedict = dict()
for year, month in product(range(2013, 2024), range(1, 13)):
    firstdate = datetime(year, month, 1)
    monthstr = (firstdate.strftime('%Y-%b')).upper()
    monthstr = '%s-%s'%(monthstr[-3:].upper(), monthstr[2:4])
    setdatedict[monthstr] = getsetdate(monthstr)

setdatestrdict = {monthstr: setdate.strftime('%Y-%m-%d') for monthstr, setdate in setdatedict.items()}
setdatestrlist = list(setdatestrdict.values())
setdatestrlist.sort()
setdatelist = list(setdatedict.values())
setdatelist.sort()

### Non-settlement dates
hkexdaydict = {year: get_hkexday_year(year) for year in range(2017, 2023)}
hkexnonsetdaydict = dict()

for year in range(2017, 2023):
    setdateset = set([datestr for datestr in setdatestrlist if datestr[:4] == str(year)])
    hkexdateset = set(hkexdaydict[year]).difference(setdateset)
    hkexdatelist = list(hkexdateset)
    hkexdatelist.sort()
    hkexnonsetdaydict[year] = hkexdatelist
