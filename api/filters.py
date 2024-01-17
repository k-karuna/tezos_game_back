from django.contrib import admin


class InputFilter(admin.SimpleListFilter):
    template = "admin/input_filter.html"

    def lookups(self, request, model_admin):
        return ((),)

    def choices(self, changelist):
        all_choice = next(super().choices(changelist))
        all_choice["query_parts"] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class DropGameIDFilter(InputFilter):
    parameter_name = 'game_hash'
    title = 'Game hash'

    def queryset(self, request, queryset):
        if self.value() is not None:
            game_hash = self.value()
            return queryset.filter(game__hash__contains=game_hash)


class DropPlayerFilter(InputFilter):
    parameter_name = 'player_address'
    title = 'Player address'

    def queryset(self, request, queryset):
        if self.value() is not None:
            address = self.value()
            return queryset.filter(game__player__address__contains=address)
