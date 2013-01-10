// Knockout custom bindings

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

//Fades views in or out based on current active view
ko.bindingHandlers.isActiveView = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        var visible = ko.utils.unwrapObservable(valueAccessor());
        var allBindings = allBindingsAccessor();
        var viewClass = allBindings.viewClass;
        var jqElement = $(element);
        var otherViews;
        var numOtherViews = 0;
        var duration = 500;
        var fadeInStarted = false
        var fadeIn = function() {
            jqElement.fadeIn(duration);
        };
        
        //Does nothing if viewClass binding is not present on element
        if(visible && typeof viewClass !== 'undefined') {
            otherViews = $('.' + viewClass + ':not(#' + jqElement.attr('id') + ')');
            numOtherViews = otherViews.size();
            
            if(numOtherViews < 1) {
                fadeIn();
            }
            else {
                otherViews.each(function(i) {
                    //Fade in as a callback to the first non-hidden view, or just called if all are hidden
                    if($(this).is(':not(:hidden)')) {
                        $(this).fadeOut(duration, fadeIn);
                        fadeInStarted = true;
                    }
                    else if(i === numOtherViews - 1 && !fadeInStarted) {
                        fadeIn();
                    }
                });
            }
        }
    }
};

//Applies the given class
ko.bindingHandlers.addClass = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        $(element).addClass(ko.utils.unwrapObservable(valueAccessor()));
    }
};