# events/forms.py
from django import forms
from datetime import datetime

class EventForm(forms.Form):
    """Simple form for creating/editing events"""
    
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Summer Music Festival'
        }),
        label="Event Name"
    )
    
    description = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Brief description of your event...'
        }),
        label="Description"
    )
    
    venue_id = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label="Venue"
    )
    
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label="Date & Time"
    )
    
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '25.00'
        }),
        label="Ticket Price (£)"
    )
    
    max_tickets = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '100'
        }),
        label="Maximum Tickets"
    )
    
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Mark as featured event"
    )
    
    def __init__(self, *args, user=None, venues=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up venue choices based on user role
        if user and venues is not None:
            if user.is_site_admin():
                venue_choices = [('', 'Select a venue')] + [(v.id, v.name) for v in venues]
                self.fields['venue_id'].widget = forms.Select(
                    choices=venue_choices,
                    attrs={'class': 'form-control', 'required': True}
                )
                self.fields['venue_id'].required = True
            else:
                # Venue admins/sub-admins: hide venue selection
                self.fields['venue_id'].widget = forms.HiddenInput()
        
        # Hide featured checkbox for non-site admins
        if user and not user.is_site_admin():
            self.fields['is_featured'].widget = forms.HiddenInput()
    
    def clean_date(self):
        """Ensure the event date is in the future"""
        date = self.cleaned_data.get('date')
        if date and date <= datetime.now():
            raise forms.ValidationError("Event date must be in the future.")
        return date