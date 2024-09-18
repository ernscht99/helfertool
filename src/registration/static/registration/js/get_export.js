function get_export(export_url)
{
  let url = new URL(window.location.origin + export_url);

  let params = {
        name: $("#checkbox_name")[0].checked,
        email: $("#checkbox_email")[0].checked,
        phone: $("#checkbox_phone")[0].checked,
        shirt: $("#checkbox_shirt")[0].checked,
        nutrition: $("#checkbox_nutrition")[0].checked,
        comment: $("#checkbox_comment")[0].checked};

  $.each(params, function(key, value) {
        url.searchParams.append(key, value);
  });
  window.location.href = url.toString();
}
