from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from badges.models import SpecialBadges
from registration.decorators import archived_not_available
from registration.models import Event, Shift, HelperShift, Helper
from registration.permissions import has_access, ACCESS_STATISTICS_VIEW

from gifts.models import DeservedGiftSet, GiftSettings

from datetime import timedelta
from itertools import cycle


# colors
# TODO: get from theming config, if this is implemented
colors_primary = [
    "#1A876E",
    "#F5BE16",
    "#E747F5",
    "#A88518",
    "#2FF5C7",
]

colors_danger = [
    "#d53e54",
    "#d53e54",
    "#d5939d",
]


def _chart_doughnut(data):
    """
    Return JSON for chart.js doughnut char.

    data = [
        {
            "value": 10,
            "labal": "Test",
            "danger": False,  # optional
        },
        ...
    ]
    """
    # colors:
    primary = cycle(colors_primary)
    danger = cycle(colors_danger)

    # prepare data for chart.js
    values = [d["value"] for d in data]
    labels = [d["label"] for d in data]

    colors = []
    for d in data:
        if d.get("danger", False):
            colors.append(next(danger))
        else:
            colors.append(next(primary))

    # json for chart.js
    output = {
        "type": "doughnut",
        "data": {
            "datasets": [
                {
                    "data": values,
                    "backgroundColor": colors,
                },
            ],
            "labels": labels,
        },
        "options": {
            "cutout": "60%",
        },
    }

    return JsonResponse(output)


@login_required
@never_cache
@archived_not_available
def chart_timeline(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access(request.user, event, ACCESS_STATISTICS_VIEW):
        return JsonResponse({})

    # collect data
    timeline = {}
    for helper in event.helper_set.all():
        if not helper.is_coordinator:
            day = helper.timestamp.strftime("%Y-%m-%d")
            if day in timeline:
                timeline[day] += 1
            else:
                timeline[day] = 1

    # abort if no data found
    if len(timeline) == 0:
        return JsonResponse({})

    # add "0" value on day before first registration
    day_one = event.helper_set.order_by("timestamp").first().timestamp
    day_zero = day_one - timedelta(days=1)
    timeline[day_zero.strftime("%Y-%m-%d")] = 0

    # sum up the days
    timeline_sum_data = []
    days = sorted(timeline.keys())
    cur_sum = 0
    for day in days:
        cur_sum += timeline[day]

        timeline_sum_data.append(
            {
                "x": day,
                "y": cur_sum,
            }
        )

    # output format
    output = {
        "type": "line",
        "data": {
            "datasets": [
                {
                    "label": _("Number of helpers"),
                    "data": timeline_sum_data,
                    "borderColor": colors_primary[0],
                    "lineTension": 0.3,
                },
            ]
        },
        "options": {
            "scales": {
                "x": {
                    "type": "time",
                },
                "y": {
                    "ticks": {
                        "precision": 0,
                    }
                },
            },
            "plugins": {
                "legend": {
                    "display": False,
                }
            },
            "maintainAspectRatio": False,
        },
    }

    return JsonResponse(output)


@login_required
@never_cache
@archived_not_available
def chart_helpers(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access(request.user, event, ACCESS_STATISTICS_VIEW):
        return JsonResponse({})

    # get data
    total_helpers = event.helper_set.count()

    num_coordinators = event.all_coordinators.count()
    num_helpers = total_helpers - num_coordinators

    if event.badges:
        num_specialbadges = SpecialBadges.objects.filter(event=event).aggregate(Sum("number"))["number__sum"] or 0
    else:
        num_specialbadges = 0

    # abort if nothing to show
    if total_helpers + num_specialbadges == 0:
        return JsonResponse({})

    # output format
    data = [
        {"value": num_helpers, "label": _("Helpers")},
        {"value": num_coordinators, "label": _("Coordinators")},
    ]
    if num_coordinators:
        data.append({"value": num_specialbadges, "label": _("Special badges")})

    return _chart_doughnut(data)


@login_required
@never_cache
@archived_not_available
def chart_shifts(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access(request.user, event, ACCESS_STATISTICS_VIEW):
        return JsonResponse({})

    # get data
    total_shifts = (
        Shift.objects.filter(job__event=event).filter(unlimited=False).aggregate(Sum("number"))["number__sum"] or 0
    )
    filled_shifts = HelperShift.objects.filter(helper__event=event).filter(shift__unlimited=False).count()
    vacant_shifts = total_shifts - filled_shifts

    # abort if nothing to show
    if total_shifts == 0:
        return JsonResponse({})

    # output format
    data = [
        {"value": filled_shifts, "label": _("Filled slots")},
        {"value": vacant_shifts, "label": _("Vacant slots"), "danger": True},
    ]

    return _chart_doughnut(data)


@login_required
@never_cache
@archived_not_available
def chart_nutrition(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access(request.user, event, ACCESS_STATISTICS_VIEW):
        return JsonResponse({})

    if not event.ask_nutrition:
        JsonResponse({})

    # get data
    num_no_preference = event.helper_set.filter(nutrition=Helper.NUTRITION_NO_PREFERENCE).count()
    num_vegetarian = event.helper_set.filter(nutrition=Helper.NUTRITION_VEGETARIAN).count()
    num_vegean = event.helper_set.filter(nutrition=Helper.NUTRITION_VEGAN).count()
    num_other = event.helper_set.filter(nutrition=Helper.NUTRITION_OTHER).count()

    # abort if nothing to show
    if num_no_preference + num_vegetarian + num_vegean + num_other == 0:
        return JsonResponse({})

    # output format
    data = [
        {"value": num_no_preference, "label": _("No preference")},
        # Translators: adjective
        {"value": num_vegetarian, "label": _("Vegetarian")},
        {"value": num_vegean, "label": _("Vegan")},
        {"value": num_other, "label": _("Other")},
    ]

    return _chart_doughnut(data)


@login_required
@never_cache
@archived_not_available
def chart_shirts(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access(request.user, event, ACCESS_STATISTICS_VIEW):
        return JsonResponse({})

    if not event.gifts:
        JsonResponse({})

    required_points = GiftSettings.objects.filter(event_id=event.id).first().required_shirt_points

    query = """
        select name,shirt_size, count(*) from
        (select name, helper_id, shirt as shirt_size, sum(count) as shirt_points from
        gifts_gift join gifts_includedgift on gifts_gift.id = gifts_includedgift.gift_id
        join registration_shift_gifts on registration_shift_gifts.giftset_id = gift_set_id
        join registration_helpershift on registration_helpershift.shift_id = registration_shift_gifts.shift_id
        join registration_helper on registration_helper.id = registration_helpershift.helper_id
        where is_shirt and gifts_gift.event_id = %s group by name, helper_id, count )
        where shirt_points >= %s group by name, shirt_size
        """

    with connection.cursor() as cursor:
        cursor.execute(query, [event.id, required_points])
        result = cursor.fetchall()

        # Read a single kind of tshirt as a dataset
        dataset_names = set(row[0] for row in result)
        labels = set(row[1] for row in result)

        # Check which values are available for shirt sizes and only use the one we have data for
        shirt_choices = [row[0] for row in event.get_shirt_choices() if row[0] in labels]

        # Build empty dict
        counts = {dataset: {label: 0 for label in shirt_choices} for dataset in dataset_names}

        for dataset, label, count in result:
            counts[dataset][label] = count

        datasets = []

        for i, dataset_name in enumerate(dataset_names):
            datasets.append(
                {
                    "label": dataset_name,
                    "data": list(counts[dataset_name].values()),
                    "borderColor": colors_primary[i],
                    "backgroundColor": colors_primary[i],
                }
            )

        # output format
        data = {
            "labels": list(shirt_choices),
            "datasets": datasets,
        }

        config = {
            "type": "bar",
            "data": data,
            "options": {
                "responsive": True,
            },
        }
        return JsonResponse(config)
