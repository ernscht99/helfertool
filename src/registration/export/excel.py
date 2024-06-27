from django.utils.translation import gettext as _

import re
import xlsxwriter

# pylint: disable=E1102


class Iterator:
    """Returns ascending natural numbers beginning from 0."""

    def __init__(self):
        self.__v = -1

    def next(self):
        """Returns the next number beginning from 0."""
        self.__v += 1
        return self.__v

    def add(self, n):
        """Returns the next number beginning from 0."""
        self.__v += n
        return self.__v

    def get(self):
        """Returns the current number.

        get() should only be used after next() to get the same number again.
        """
        return self.__v

    def reset(self):
        """Resets the counter.

        The first call to next() after this returns 0."""
        self.__v = -1


def clean_name(name):
    """Cleans the name to be a valid sheet name in excel.

    The characters [ ] : * ? / \\ are removed.
    """
    return re.sub(r"[\[\]:*?\/]", "", name)


def escape(payload):
    if not payload:
        return ""

    # http://blog.zsec.uk/csv-dangers-mitigations/
    if payload[0] in ("@", "+", "-", "=", "|"):
        payload = payload.replace("|", r"\|")
        payload = "'" + payload + "'"
    return payload


def xlsx(buffer, event, jobs, date, include_sensitive, included_columns):
    """Exports the helpers for given jobs of an event as excel spreadsheet.

    Parameter:
        buffer: a writeable bytes buffer (e.g. io.BytesIO or a file)
        event:  the exported event
        jobs:   a list of all exported jobs
        date:   export only for this date
        include_sensitive: Include sensitive data in export
        included_columns: columns to include in the export {column_name: bool_include}
    """
    # create xlsx
    workbook = xlsxwriter.Workbook(buffer)

    # duplicated worksheet names are not allowed
    used_names = []

    # export jobs
    for job in jobs:
        # find unique worksheet name
        job_name = clean_name(job.name)[:20]  # worksheet name must be <= 31 chars

        job_name_use = job_name
        counter = 2
        while job_name_use in used_names:
            job_name_use = "{}{}".format(job_name, counter)
            counter += 1

        used_names.append(job_name_use)

        # add things
        worksheet = workbook.add_worksheet(job_name_use)
        bold = workbook.add_format({"bold": True})
        multiple_shifts = workbook.add_format({"bg_color": "#fFFF99"})

        row = Iterator()
        column = Iterator()

        # determine which of the requested columns are included
        included_columns["phone"] = event.ask_phone and included_columns["phone"] and include_sensitive
        included_columns["shirt"] = event.ask_shirt and included_columns["shirt"]
        included_columns["nutrition"] = event.ask_nutrition and included_columns["nutrition"]
        included_columns["foodhandling"] = job.infection_instruction and included_columns["foodhandling"]

        # header
        if included_columns["name"]:
            worksheet.write(0, column.next(), _("First name"), bold)
            worksheet.write(0, column.next(), _("Surname"), bold)
            worksheet.set_column(0, column.get(), 30)
        if included_columns["email"]:
            worksheet.write(0, column.next(), _("E-Mail"), bold)
            worksheet.set_column(0, column.get(), 30)

        if included_columns["phone"]:
            worksheet.write(0, column.next(), _("Mobile phone"), bold)
            worksheet.set_column(column.get(), column.get(), 20)

        if included_columns["shirt"]:
            worksheet.write(0, column.next(), _("T-shirt"), bold)
            worksheet.set_column(column.get(), column.get(), 10)

        if included_columns["nutrition"]:
            worksheet.write(0, column.next(), _("Nutrition"), bold)
            worksheet.set_column(column.get(), column.get(), 13)

        if included_columns["foodhandling"]:
            worksheet.write(0, column.next(), _("Food handling"), bold)
            worksheet.set_column(column.get(), column.get(), 20)

        if included_columns["comment"]:
            worksheet.write(0, column.next(), _("Comment"), bold)
            worksheet.set_column(column.get(), column.get(), 50)

        # last column, needed for merge later
        last_column = column.get()

        # freeze header
        worksheet.freeze_panes(1, 0)

        # skip first row
        row.next()

        # coordinators
        if not date and job.coordinators.exists():
            worksheet.merge_range(row.next(), 0, row.get(), last_column, _("Coordinators"), bold)
            add_helpers(worksheet, row, column, event, job, job.coordinators.all(), multiple_shifts, include_sensitive)

        # show all shifts
        for shift in job.shift_set.order_by("begin"):
            if date and shift.date() != date:
                continue

            worksheet.merge_range(row.next(), 0, row.get(), last_column, shift.time(), bold)
            add_helpers(worksheet, row, column, event, job, shift.helper_set.all(), multiple_shifts, included_columns)

    # close xlsx
    workbook.close()


def add_helpers(worksheet, row, column, event, job, helpers, multiple_shifts_format, included_columns):
    for helper in helpers:
        row.next()
        column.reset()

        num_shifts = helper.shifts.count()
        num_jobs = len(helper.coordinated_jobs)
        cell_format = None
        if num_shifts + num_jobs > 1:
            cell_format = multiple_shifts_format

        if included_columns["name"]:
            worksheet.write(row.get(), column.next(), escape(helper.firstname), cell_format)
            worksheet.write(row.get(), column.next(), escape(helper.surname), cell_format)
        if included_columns["email"]:
            worksheet.write(row.get(), column.next(), escape(helper.email), cell_format)
        if included_columns["phone"]:
            worksheet.write(row.get(), column.next(), escape(helper.phone), cell_format)
        if included_columns["shirt"]:
            worksheet.write(row.get(), column.next(), escape(str(helper.get_shirt_display())), cell_format)
        if included_columns["nutrition"]:
            worksheet.write(row.get(), column.next(), escape(str(helper.get_nutrition_short())), cell_format)
        if included_columns["foodhandling"]:
            worksheet.write(
                row.get(), column.next(), escape(str(helper.get_infection_instruction_short())), cell_format
            )
        if included_columns["comment"]:
            worksheet.write(row.get(), column.next(), escape(helper.comment), cell_format)
