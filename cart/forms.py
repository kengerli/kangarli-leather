from django import forms

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 11)]

class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=PRODUCT_QUANTITY_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    size = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        # 1. Intercept the product object (if passed) before the standard form initialization
        product = kwargs.pop('product', None)
        super(CartAddProductForm, self).__init__(*args, **kwargs)

        # 2. Default option (for bags, wallets, etc.)
        dynamic_choices = [('Standard', 'Standard Size')]

        # 3. If a product is passed, check its category
        if product:
            # Get the names of the current category and parent (in lowercase for convenience)
            cat_name = product.category.name.lower()
            parent_name = product.category.parent.name.lower() if product.category.parent else ""
            combined_name = f"{cat_name} {parent_name}"

            # SIZE LOGIC (You can add new categories here later)
            if 'shoe' in combined_name or 'boot' in combined_name:
                dynamic_choices = [(str(i), f'Size {i}') for i in range(39, 46)]             
            elif 'ring' in combined_name:
                dynamic_choices = [(str(i), f'Size {i}') for i in range(15, 23)]               
            elif 'belt' in combined_name:
                dynamic_choices = [('85', '85 cm'), ('90', '90 cm'), ('95', '95 cm'), ('100', '100 cm'), ('105', '105 cm')]

            elif 'hat' in combined_name:
                dynamic_choices = [('S', 'Small (55 cm)'), ('M', 'Medium (57 cm)'), ('L', 'Large (59 cm)'), ('XL', 'Extra Large (61 cm)')]

            elif 'jacket' in combined_name:
                dynamic_choices = [
                    ('S', 'Small (48)'), 
                    ('M', 'Medium (50)'), 
                    ('L', 'Large (52)'), 
                    ('XL', 'Extra Large (54)'), 
                    ('XXL', 'XXL (56)')
                ]
        # 4. Apply the generated list to our size field
        self.fields['size'].choices = dynamic_choices