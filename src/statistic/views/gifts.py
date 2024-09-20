from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count, Q
from helfertool.utils import nopermission
from registration.decorators import archived_not_available
from registration.models import Event, Helper
from registration.permissions import has_access, has_access_event_or_job, ACCESS_STATISTICS_VIEW

from gifts.models import IncludedGift


@login_required
@never_cache
@archived_not_available
def gifts(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # permission
    if not has_access_event_or_job(request.user, event, ACCESS_STATISTICS_VIEW):
        return nopermission(request)

    # check if nutrition is collected for this event
    if not event.ask_nutrition:
        context = {"event": event}
        return render(request, "statistic/gifts_not_active.html", context)

    # Update Gifts in database
    helper_list = Helper.objects.filter(shifts__job__event=event)

    for helper in helper_list:
        helper.gifts.update()

    # Generate General Gift stats
    gift_data = (
        IncludedGift.objects.values("gift__name")  # Group by gift name
        .annotate(total=Sum("count"))  # Total gifts given (delivered + not delivered)
        .annotate(delivered=Sum("count", filter=Q(gift_set__deservedgiftset__delivered=True)))  # Only delivered gifts
    )

    # render
    context = {"event": event, "gift_data": gift_data}
    return render(request, "statistic/gifts.html", context)
