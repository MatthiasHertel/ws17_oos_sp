
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

class UtilsService:
    def hello(self):
        print("testclass")

    def validate_date(self, date):
        date = date.replace('-', '')
        try:
            date_obj = self.make_date_from(date)
        except Exception as e:
            raise Exception("Date is not in the valid format: %s" % e)

    def make_date_from(self, yyyymmdd):
        yyyymmdd = yyyymmdd.replace('-', '')

        year = int(str(yyyymmdd)[0:4])
        month = int(str(yyyymmdd)[4:6])
        try:
            day = int(str(yyyymmdd)[6:8])
        except:
            day = 1

        re = date(year, month, day)
        return re

    def get_month_range(self, first_date, last_date=None, excluding=None):
        months = []

        first = self.make_date_from(first_date)
        if last_date:
            cursor = make_date_from(last_date)
        else:
            cursor = datetime.utcnow().date()

        if excluding:
            (x_year, x_month) = excluding.split('-')
        else:
            x_year = x_month = "0"

        while cursor.year > first.year or cursor.month >= first.month and cursor.year >= 2010:
            if not(cursor.year == int(x_year) and cursor.month == int(x_month)):
                months.append(cursor)
            # logger.info("have cursor %s, first %s - moving back by 1 month" % (cursor, first))
            cursor = cursor - relativedelta(months=1)

        return months


    def get_dates_range(self, first_date):
        first = make_date_from(first_date)

        cursor = datetime.utcnow().date() # TODO use profile TZ?
        days = []

        # there is something badly wrong here
        while cursor >= first:
            days.append(cursor)
            cursor = cursor - timedelta(days=1)

        return days


    def get_days_using(self, first_date):
        first = self.make_date_from(first_date)
        now = datetime.utcnow().date()

        delta = now-first
        return delta.days


    def get_month_name(self, yyyymm):
        month = int(str(yyyymm)[4:6])
        # generating month name from month int
        mstr = date(1900, month, 1).strftime('%B')
        return mstr


    def get_year_name(self, yyyymm):
        year = int(str(yyyymm)[0:4])
        return str(year)


    def make_summaries(self, day):
        returned = {}
        lookup = {'walking': 'walking', 'running': 'ran', 'cycling': 'cycled', 'transport': 'Transport'}

        if not day['summary']:
            return {'walking': 'No activity'}

        for summary in day['summary']:
            returned[summary['activity']] = self.make_summary(summary, lookup)

        return returned


    def make_summary(self, object, lookup):
        return "%s for %.1f km, taking %i minutes" % (lookup[object['activity']],
                float(object['distance'])/1000, float(object['duration'])/60)


    def geojson_place(self, segment):
        feature = {'type': 'Feature', 'geometry': {}, 'properties': {}}

        coordinates = [segment['place']['location']['lon'], segment['place']['location']['lat']]
        feature['geometry'] = {"type": "Point", "coordinates": coordinates}

        for key in segment.keys():
            # TODO convert activity?
            feature['properties'][key] = segment[key]

        # make a nice duration number as well
        # print(segment['startTime'])
        # start = datetime.strptime(segment['startTime'], '%Y%m%dT%H%M%Sz')
        # end = datetime.strptime(segment['endTime'], '%Y%m%dT%H%M%Sz')
        # duration = end-start
        # feature['properties']['duration'] = duration.seconds

        # name and description
        if 'name' in segment['place']:
            feature['properties']['title'] = segment['place']['name']
        else:
            feature['properties']['title'] = "Unknown"

        if 'foursquareId' in segment['place']:
            feature['properties']['url'] = "https://foursquare.com/v/"+segment['place']['foursquareId']

        # styling
        feature['properties']['icon'] = {
            "iconUrl": "/static/images/circle-stroked-24.svg",
            "iconSize": [24, 24],
            "iconAnchor": [12, 12],
            "popupAnchor": [0, -12]
        }

        return feature


    def geojson_move(self, segment):
        features = []
        lookup = {'walking': 'Walking', 'transport': 'Transport', 'run': 'Running', 'cycling': 'Cycling'}
        stroke = {'walking': '#00d45a', 'transport': '#000000', 'run': '#93139a', 'cycling': '#00ceef'}
        # print ("\n\n\n\n\n\n\n\n\n\n\{}".format(segment))
        for activity in segment['activities']:
            trackpoints = activity['trackPoints']
            coordinates = [[point['lon'], point['lat']] for point in trackpoints]
            timestamps = [point['time'] for point in trackpoints]
            geojson = {'type': 'Feature', 'geometry': {}, 'properties': {}}
            geojson['geometry'] = {'type': 'LineString', 'coordinates': coordinates}
            for key in activity.keys():
                if key != 'trackPoints':
                    geojson['properties'][key] = activity[key]

            # add a description & the saved timestamps
            geojson['properties']['description'] = self.make_summary(activity, lookup)
            geojson['properties']['times'] = timestamps

            # add styling
            geojson['properties']['stroke'] = stroke[activity['activity']]
            geojson['properties']['stroke-width'] = 3
            if activity['activity'] == 'trp':
                geojson['properties']['stroke-opacity'] = 0.1

            features.append(geojson)

        return features
