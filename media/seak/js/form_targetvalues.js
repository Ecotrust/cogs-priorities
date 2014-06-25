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

$('.category-buttons').children(".btn").click(function(){
    var value = $(this).val();
    $(this).parent().find("button").removeClass('active');
    $(this).addClass('active');
    $(this).closest('.accordion-group-objective').find('.accordion-body .btn').removeClass('active');
    $(this).closest('.accordion-group-objective').find('.accordion-body button[value="' + value + '"]').addClass('active');
    $(this).closest('.accordion-group-objective').find('.accordion-body .targetvalue').val(value).change();
});

$('.target-buttons').children(".btn").click(function(){
    var value = $(this).val();
    $(this).parent().find("button").removeClass('active');
    $(this).addClass('active');
    $(this).parent().parent().find('.targetvalue').val(value)
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