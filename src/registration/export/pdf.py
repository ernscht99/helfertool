from django.utils.translation import gettext as _

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

# styles
par_style = getSampleStyleSheet()["Normal"]
h1_style = getSampleStyleSheet()["Heading1"]
h2_style = getSampleStyleSheet()["Heading2"]
table_style = TableStyle(
    [
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)

margin = 1.5 * cm


def h1(text):
    return Paragraph(text, h1_style)


def h2(text):
    return Paragraph(text, h2_style)


def par(text):
    return Paragraph(text, par_style)


def add_table(elements, data, widths):
    t = Table(data, widths, hAlign="LEFT")
    t.setStyle(table_style)
    elements.append(t)


def table_of_helpers(elements, helpers, event, included_columns):
    # determine which of the requested columns are included
    included_columns["phone"] = event.ask_phone and included_columns["phone"]
    included_columns["shirt"] = event.ask_shirt and included_columns["shirt"]
    included_columns["nutrition"] = event.ask_nutrition and included_columns["nutrition"]

    # table
    available_space = 17  # 17cm are the total possible width
    spaces = []
    header = []

    def add_column(heading, space, available_space):
        if available_space - space < 0:
            return
        header.append(par(heading))
        spaces.append(space)
        return available_space - space

    if included_columns["name"]:
        available_space = add_column(_("Name"), 5, available_space)
    if included_columns["email"]:
        available_space = add_column(_("E-Mail"), 5, available_space)
    if included_columns["phone"]:
        available_space = add_column(_("Phone"), 3, available_space)
    if included_columns["shirt"]:
        available_space = add_column(_("T-shirt"), 1.5, available_space)
    if included_columns["nutrition"]:
        available_space = add_column(_("Nutrition"), 2.5, available_space)
    if included_columns["foodhandling"]:
        available_space = add_column(_("Food Handling Instructions"), 4, available_space)
    if included_columns["comment"]:
        available_space = add_column(_("Comment"), available_space, available_space)

    # guard against not selecting any columns
    if not header:
        add_column("", 4, available_space)

    data = [
        header,
    ]

    for helper in helpers:
        tmp = []
        if included_columns["name"]:
            tmp.append(par("%s %s" % (helper.firstname, helper.surname)))
        if included_columns["email"]:
            tmp.append(par(helper.email))
        if included_columns["phone"]:
            tmp.append(par(helper.phone))
        if included_columns["shirt"]:
            tmp.append(par(helper.get_shirt_display()))
        if included_columns["nutrition"]:
            tmp.append(par(helper.get_nutrition_short()))
        if included_columns["foodhandling"]:
            tmp.append(par(helper.get_infection_instruction_short()))
        if included_columns["comment"]:
            tmp.append(par(helper.comment))
        data.append(tmp)

    spaces = [s * cm for s in spaces]
    add_table(elements, data, spaces)


def pdf(buffer, event, jobs, date, included_columns):
    doc = SimpleDocTemplate(buffer, topMargin=margin, rightMargin=margin, bottomMargin=margin, leftMargin=margin)
    doc.pagesize = A4

    # elements
    elements = []

    # iterate over jobs
    for job in jobs:
        # heading
        heading = h1("%s" % job.name)
        elements.append(heading)

        # coordinators
        if not date and job.coordinators.exists():
            heading = h2(_("Coordinators"))
            elements.append(heading)

            table_of_helpers(elements, job.coordinators.all(), event, included_columns)

        # iterate over shifts
        for shift in job.shift_set.all():
            if date and shift.date() != date:
                continue

            heading = h2(f"{shift.time_with_day()}: {shift.name}")
            elements.append(heading)

            if shift.helper_set.count() > 0:
                table_of_helpers(elements, shift.helper_set.all(), event, included_columns)
            else:
                p = par(_("Nobody is registered for this shift."))
                elements.append(p)

        # page break
        elements.append(PageBreak())

    # build pdf
    doc.build(elements)
