$('.category-buttons').children(".btn").click(function(){
    var value = $(this).val();
    $(this).parent().find("button").removeClass('active');
    $(this).addClass('active');

    //old 'apply' logic
    var targetval = value;
    // var penaltyval = $(this).parent().parent().parent().parent().find('.penaltyvalue').val();
    // $(this).closest('.accordion-group-objective').find('.accordion-body .slider-range-single').slider('value', penaltyval); 
    // $(this).closest('.accordion-group-objective').find('.accordion-body .slider-range-penalty').slider('value', penaltyval); 
    // $(this).closest('.accordion-group-objective').find('.accordion-body .slider-range-target').slider('value', targetval); 
    // $(this).closest('.accordion-group-objective').find('.accordion-body .penaltyvalue').val(penaltyval).change();
    $(this).closest('.accordion-group-objective').find('.accordion-body .btn').removeClass('active');
    $(this).closest('.accordion-group-objective').find('.accordion-body button[value="' + value + '"]').addClass('active');
    $(this).closest('.accordion-group-objective').find('.accordion-body .targetvalue').val(targetval).change();
});

$('.target-buttons').children(".btn").click(function(){
    var value = $(this).val();
    $(this).parent().find("button").removeClass('active');
    $(this).addClass('active');
    var targetval = value;
    $(this).parent().parent().find('.targetvalue').val(value)
});

$('.targetvalue').change( function(e) { 
    var targetPrefixes = ['singlerange', 'targetrange'];
    var len = targetPrefixes.length;
    for (var i=0; i<len; ++i) {
        var pre = targetPrefixes[i];
        sliderTargetId = $(this).attr('id').replace("target",pre) 
        sliderTarget = $("#" + sliderTargetId)
        sliderTarget.slider( "option", "value", $(this).val() );
    }
});

$('.categoryvalue').change( function(e) { 
    sliderTargetId = $(this).attr('id').replace("categorytarget",'') 
    sliderTarget = $("#" + sliderTargetId)
    sliderTarget.slider( "option", "value", $(this).val() );
});

// When collapsing details, show the aggregate sliderbar and vice-versa
$('.cf-collapse').on('hide', function() {
    $(this).parent().find(".category-icon").removeClass("icon-minus"); 
    $(this).parent().find(".category-icon").addClass("icon-plus"); 
});
$('.cf-collapse').on('show', function() {
    $(this).parent().find(".category-icon").removeClass("icon-plus"); 
    $(this).parent().find(".category-icon").addClass("icon-minus"); 
});