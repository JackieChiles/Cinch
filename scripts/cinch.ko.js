// Knockout custom bindings

ko.bindingHandlers.jqmButtonEnabled = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        //Need a try-catch to handle when this is called before JQM initialization of the control
        try {
            var enable = ko.utils.unwrapObservable(valueAccessor());
            
            if(enable) {
                if($(element).attr('data-role') === 'button') {
                    //"Link" buttons
                    $(element).removeClass('ui-disabled');
                    $(element).addClass('ui-enabled');
                }
                else {
                    //Inputs or button elements
                    $(element).button('enable');
                }
            }
            else {
                if($(element).attr('data-role') === 'button') {
                    $(element).removeClass('ui-enabled');
                    $(element).addClass('ui-disabled');
                }
                else {
                    $(element).button('disable');
                }
            }
        }
        catch (e) {
        }
    }
};

//Cbr stands for checkboxradio
ko.bindingHandlers.jqmCbrEnabled = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        //Need a try-catch to handle when this is called before JQM initialization of the control
        try {
            var enable = ko.utils.unwrapObservable(valueAccessor());
            
            if(enable) {
                $(element).checkboxradio('enable');
            }
            else {
                $(element).checkboxradio('disable');
            }
        }
        catch (e) {
        }
    }
};

//Applies a border for emphasis if condition is met
ko.bindingHandlers.activeBorder = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        var enable = ko.utils.unwrapObservable(valueAccessor());
        
        if(enable) {
            $(element).addClass('active-border');
        }
        else {
            $(element).removeClass('active-border');
        }
    }
};

//Applies the given class
ko.bindingHandlers.addClass = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        $(element).addClass(ko.utils.unwrapObservable(valueAccessor()));
    }
};