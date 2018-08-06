from django import forms
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from pretalx.submission.models import Submission, SubmissionStates, SubmissionType


class InfoForm(forms.ModelForm):
    def __init__(self, event, **kwargs):
        self.event = event
        readonly = kwargs.pop('readonly', False)
        instance = kwargs.get('instance')
        initial = kwargs.pop('initial', {})
        initial['submission_type'] = getattr(
            instance, 'submission_type', self.event.cfp.default_type
        )
        initial['content_locale'] = getattr(
            instance, 'content_locale', self.event.locale
        )

        super().__init__(initial=initial, **kwargs)

        self.fields['abstract'].widget.attrs['rows'] = 2
        for key in {'abstract', 'description', 'notes', 'image', 'do_not_record'}:
            request = event.settings.get(f'cfp_request_{key}')
            require = event.settings.get(f'cfp_require_{key}')
            if not request:
                self.fields.pop(key)
            else:
                self.fields[key].required = require
        self.fields['submission_type'].queryset = SubmissionType.objects.filter(
            event=self.event
        )
        _now = now()
        if (
            not self.event.cfp.deadline or self.event.cfp.deadline >= _now
        ):  # No global deadline or still open
            types = self.event.submission_types.exclude(deadline__lt=_now)
        else:
            types = self.event.submission_types.filter(deadline__gte=_now)
        pks = set(types.values_list('pk', flat=True))
        if instance and instance.pk:
            pks |= {instance.submission_type.pk}
        self.fields['submission_type'].queryset = self.event.submission_types.filter(
            pk__in=pks
        )

        locale_names = dict(settings.LANGUAGES)
        self.fields['content_locale'].choices = [
            (a, locale_names[a]) for a in self.event.locales
        ]

        if readonly:
            for f in self.fields.values():
                f.disabled = True

    class Meta:
        model = Submission
        fields = [
            'title',
            'submission_type',
            'content_locale',
            'abstract',
            'description',
            'notes',
            'do_not_record',
            'image',
        ]


class SubmissionFilterForm(forms.ModelForm):
    state = forms.MultipleChoiceField(
        choices=SubmissionStates.get_choices(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, event, *args, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)
        self.fields['submission_type'].queryset = self.fields[
            'submission_type'
        ].queryset.filter(event=event)
        self.fields['submission_type'].required = False
        self.fields['state'].required = False
        sub_count = lambda x: event.submissions.filter(state=x).count()
        self.fields['state'].choices = [
            (choice[0], f'{choice[1].capitalize()} ({sub_count(choice[0])})')
            for choice in self.fields['state'].choices
        ]

    class Meta:
        model = Submission
        fields = ['submission_type', 'state']
