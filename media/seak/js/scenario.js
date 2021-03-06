var LOW_SCENARIO_TARGET = 5;
var MED_SCENARIO_TARGET = 10;
var HIGH_SCENARIO_TARGET = 25;

function progressViewModel() {
  var self = this;

  self.progressHtml = ko.observable();
  self.done = ko.observable(false);
  self.error = ko.observable(false);
  self.progressBarWidth = ko.observable("0%");
  self.triggerDone = function(scenario_uid) {
    clearInterval(app.timer);
    app.timer = null;
    if (scenario_uid) {
        app.viewModel.scenarios.loadScenarios(scenario_uid);
    }
    // not "done" until the new report loads, just keep the 100% progress bar up and spinning
  };
  self.checkTimer = function() {
    var checkProgress = function () {
        var url = $('#selected_progress_url').attr('value');
        var marxan_portion = 0.8; // marxan takes x percent of the total runtime, rest is compiling results
        var selected = app.viewModel.scenarios.selectedFeature();
        if (!selected) {
            clearInterval(app.timer);
            app.timer = null;
            return false;
        }
        if (!self.done() && !selected.done()) {
            $.get(url, function(data) {
                self.progressHtml(data.html);
                if (data.error == 1) {
                    self.error(true);
                    app.viewModel.scenarios.selectedFeature().error(true);
                    // stop timer without declaring done
                    clearInterval(app.timer);
                    app.timer = null;
                }
                var pct = parseInt((data.complete / data.total) * 100.0, 10);

                self.progressBarWidth(2 + (pct * marxan_portion) + "%");
                if (pct >= 100) {
                    uid = app.viewModel.scenarios.selectedFeature().uid();
                    self.triggerDone(uid);
                }
            });
        }
        var elem = $('#scenario_progress_html');  // if this doesn't exist, instance is done
        if (elem.length === 0) {
            self.triggerDone();
            // Only show the layer if we're getting a fresh layer with a completed status
            app.viewModel.scenarios.toggleScenarioLayer('on');
            return false;
        }
    };
    if (!app.timer) {
        checkProgress();
        app.timer = setInterval(checkProgress, 2000);
    } else {
        console.log("Warning: app.timer is set and checkTimer was called!");
    }
 };
  
  return self;
}

function scenariosViewModel() {
  var self = this;

  // this will get bound to the active scenario
  self.selectedFeature = ko.observable(false);
  // display the form panel entirely
  self.showScenarioPanels = ko.observable();
  // display initial help
  self.showScenarioHelp = ko.observable(true);
  // display form
  self.showScenarioFormPanel = ko.observable(false);
  // display list of scenarios
  self.showScenarioList = ko.observable(true);
  self.scenarioLoadError = ko.observable(false);
  self.scenarioLoadComplete = ko.observable(false);
  self.reportLoadError = ko.observable(false);
  self.reportLoadComplete = ko.observable(false);
  self.planningUnitsLoadError = ko.observable(false);
  self.planningUnitsLoadComplete = ko.observable(false);
  self.formLoadError = ko.observable(false);
  self.formLoadComplete = ko.observable(true);
  self.formSaveError = ko.observable(false);
  self.formSaveComplete = ko.observable(true);
  // list of all scenarios, primary viewmodel
  self.scenarioList = ko.observableArray();
  // display mode
  self.dataMode = ko.observable('manage');

  // pagination config will display x items 
  // from this zero based index
  self.listStart = ko.observable(0);
  self.listDisplayCount = 9;

  // paginated list
  self.scenarioListPaginated = ko.computed(function () {
    return self.scenarioList.slice(self.listStart(), self.listDisplayCount+self.listStart());
  });

  self.switchMode = function(mode) {
    if (self.dataMode() == mode) {
        // no need to switch or reload
        return;
    }
    self.dataMode(mode);
    self.selectedFeature(false);
    self.showScenarioList(true);
    self.cancelAddScenario();
    self.loadScenarios();
  };
  
  // this list is model for pagination controls 
  self.paginationList = ko.computed(function () {
    var list = [], listIndex = 0, displayIndex = 1;
    for (listIndex=0; listIndex < self.scenarioList().length; listIndex++) {
      if (listIndex % self.listDisplayCount === 0) {
        list.push({'displayIndex': 1 + (listIndex/self.listDisplayCount), 'listIndex': listIndex });
      }
    }
    if (list.length < self.scenarioList().length / self.listDisplayCount) {
      list.push({'displayIndex': '...', 'listIndex': null });
      list.push({'displayIndex': '»', 'listIndex': null });

    }
    return list;
  });

  self.setListIndex = function (button, event) {
    var listStart = self.listStart();
    if (button.displayIndex === '»') {
        self.listStart(listStart + self.listDisplayCount * 5);
    } else {
        self.listStart(button.listIndex);
    }
  };


  self.showScenarioForm = function(action, uid) {
    self.toggleScenarioLayer('off');  // Don't show the layer while being edited/created

    var formUrl;
    if (action === "create") {
      formUrl = app.workspaceUtil.actions.getByRel("create")[0].getUrl();
    } else if (action === "edit") {
      formUrl = app.workspaceUtil.actions.getByTitle("Edit")[0];
      formUrl = formUrl.getUrl([uid]);
    }

    // Get a lookup dict for id to dbf fieldname conversion
    var lookup_url = "/seak/id_lookup.json";
    var idLookup;
    var xhr = $.ajax({
        url: lookup_url,
        cache: true,
        dataType: 'json',
        success: function(data) {
            idLookup = data;
        }
    })
    .error( function() {
        idLookup = null;
    });

    var applySliders = function() {
        //getGeographyFieldInfo();
        $.each( $(".slider-range-single"), function(k, sliderrange) {
            var id = $(sliderrange).attr('id');
            id = id.replace("singlerange---", '');
            $(sliderrange).slider({
                range: "min",
                value: 0,
                min: 0,
                max: 100,
                change: function( event, ui ) {
                    $( "#penalty---" + id ).val( ui.value );
                    $( "#target---" + id ).val( ui.value );
                },
                slide: function( event, ui ) {
                    $( "#penalty---" + id ).val( ui.value );
                    $( "#target---" + id ).val( ui.value );
                }
            });
        });
        
        $.each( $(".slider-range-penalty"), function(k, sliderrange) {
            var id = $(sliderrange).attr('id');
            id = id.replace("penaltyrange---", '');
            $(sliderrange).slider({
                range: "min",
                value: 0,
                min: 0,
                max: 100,
                change: function( event, ui ) {
                    $( "#penalty---" + id ).val( ui.value );
                },
                slide: function( event, ui ) {
                    $( "#penalty---" + id ).val( ui.value );
                }
            });
        });

        $.each( $(".slider-range-target"), function(k, sliderrange) {
            var id = $(sliderrange).attr('id');
            id = id.replace("targetrange---", '');
            $(sliderrange).slider({
                range: "min",
                value: 0,
                min: 0,
                max: 100,
                change: function( event, ui ) {
                    $( "#target---" + id ).val( ui.value );
                },
                slide: function( event, ui ) {
                    $( "#target---" + id ).val( ui.value );
                }
            });
        });
    };

    // clean up and show the form
    var jqxhr = $.get(formUrl, function(data) {
      $('#scenarios-form-container').empty().append(data);
      var $form = $('#scenarios-form-container').find('form#featureform');
      $form.find('input:submit').remove();
      self.showScenarioFormPanel(true);
    })
    .success( function() {
        self.showScenarioList(false);
        self.selectedFeature(false);
        self.showScenarioList(false);

        // If we're in EDIT mode, set the form values 
        if ($('#id_input_targets').val() &&
            $('#id_input_penalties').val() &&
            $('#id_input_relativecosts').val()) {
 
            // Reset to zeros 
            $.each( $('.targetvalue'), function(k, target) { $(target).val(0); });
            $.each( $('.penaltyvalue'), function(k, penalty) { $(penalty).val(0); });
            $.each( $('.costvalue'), function(k, cost) { $(cost).removeAttr('checked'); });
             
            applySliders();

            // Apply Costs
            var in_costs = JSON.parse($('#id_input_relativecosts').val());
            $.each(in_costs, function(key, val) {
                if (val > 0) {
                    $("#cost---" + key).attr('checked','checked');
                } else {
                    $("#cost---" + key).removeAttr('checked');
                }
            });
            // Apply Targets and Penalties
            var in_targets = JSON.parse($('#id_input_targets').val());
            $.each(in_targets, function(key, val) {
                $("#target---" + key).val(val * 100);
                $("#targetrange---" + key).slider("value", val * 100);
                if (val * 100 == LOW_SCENARIO_TARGET || val * 100 == MED_SCENARIO_TARGET || val * 100 == HIGH_SCENARIO_TARGET || val * 100 == 0) {
                    $("#singlerange---" + key).find('button[value="' + val * 100 + '"]').addClass('active');
                }
                if (val > 0 ) {
                    $('#singlerange---' + key).closest(".accordion-group").find('.cf-collapse').collapse();
                }
            });
            var in_penalties = JSON.parse($('#id_input_penalties').val());
            $.each(in_penalties, function(key, val) {
                $("#penalty---" + key).val(val * 100);
                $("#penaltyrange---" + key).slider("value", val * 100);
            });
            // end "if EDIT" mode
        } else {
            applySliders();
        }

        // Bindings for tab navigation
        $('a[data-toggle="tab"]').on('show', function (e) {
            e.preventDefault();
            // The tab that was previously selected
            switch (e.relatedTarget.id) {
                case "tab-geography":
                    utfClickControl.activate();
                    //selectGeographyControl.deactivate();
                    keyboardControl.deactivate();
                    break;
                case "tab-costs":
                    break;
                case "tab-species":
                    break;
            }

            // The newly selected tab 
            switch (e.target.id) {
                case "tab-geography":
                    //selectGeographyControl.activate();
                    keyboardControl.activate();
                    utfClickControl.deactivate();
                    break;
                case "tab-costs":
                    break;
                case "tab-species":
                    $.each($('div.accordion-group-objective'), function() {
                        $(this).removeClass('hide');
                        if($(this).find('tr.cf-row:not(.hide)').length === 0) {
                            $(this).addClass('hide');
                        }
                    });
                    $.each( $(".slider-range"), function(idx, a){
                        // set the value to trigger slider change event
                        var b = $(a).slider("value");
                        $(a).slider("value", b);
                    });
                    break;
            }
        });
    })
    .error( function() { self.formLoadError(true); } )
    .complete( function() { self.formLoadComplete(true); } );
  };

  self.saveScenarioForm = function(self, event) {
        var targets = {};
        var penalties = {};
        var costs = {};
        var totaltargets = 0;
        var totalpenalties = 0;

        // Get targets
        $("#form-cfs tr.cf-row:not(.hide) input.targetvalue").each( function(index, elem) {
            var xid = $(elem).attr("id");
            var id = "#" + xid;
            xid = xid.replace(/^target---/,''); //  Remove preceding identifier
            xid = xid.replace(/---$/,''); // Remove trailing ---
            targets[xid] = parseFloat($(id).val()) / 100.0;
            totaltargets += targets[xid];
        });
        // Get penalties 
        $("#form-cfs tr.cf-row:not(.hide) input.penaltyvalue").each( function(index, elem) {
            var xid = $(elem).attr("id");
            var id = "#" + xid;
            xid = xid.replace(/^penalty---/,'');
            xid = xid.replace(/---$/,'');
            penalties[xid] = parseFloat($(id).val()) / 100.0;
            totalpenalties += penalties[xid];
        });
        // Initialize costs to zero
        $('#form-costs input:checkbox.costvalue').each( function(index) {
            var xid = $(this).attr("id");
            xid = xid.replace(/^cost---/,'');
            costs[xid] = 0;
        });
        // Set the *checked* costs to 1
        $('#form-costs .cost-row:not(.hide) input:checkbox.costvalue:checked').each( function(index) {
            var xid = $(this).attr("id");
            xid = xid.replace(/^cost---/,'');
            costs[xid] = 1;
        });

        // Set the form values (note that .html() doesnt change)
        var frm = $('form#featureform');
        $(frm).find('textarea#id_input_targets').val( JSON.stringify(targets) );
        $(frm).find('textarea#id_input_penalties').val( JSON.stringify(penalties) );
        $(frm).find('textarea#id_input_relativecosts').val( JSON.stringify(costs) );

        if (totalpenalties === 0 || totaltargets === 0) {
            alert("Please complete the scenario form");
            $("#formtabs a[href='#speciestab']").tab('show');
        } else if ($(frm).find('input[name="name"]').val() === '') {
            alert("Please complete the scenario form");
            $("#formtabs a[href='#generaltab']").tab('show');
            $(frm).find('input[name="name"]').focus();
        } else {
            // GO .. we are clear to submit the form
            $('#button-save-scenario').attr('disabled',true);
            var values = {};
            var actionUrl = $(frm).attr('action');
            $(frm).find('input,select,textarea').each(function() {
                values[$(this).attr('name')] = $(this).val();
            });

            // Submit the form
            self.formSaveComplete(false);
            self.formSaveError(false);
            var scenario_uid;
            var jqxhr = $.ajax({
                url: actionUrl,
                type: "POST",
                data: values
            })
            .success( function(data, textStatus, jqXHR) {
                var d = JSON.parse(data);
                scenario_uid = d["X-Madrona-Select"];
                self.loadScenarios(scenario_uid);

                //self.cancelAddScenario(); // Not acutally cancel, just clear 
                self.showScenarioFormPanel(false);
                self.showScenarioList(true);
                self.formSaveError(false);
            })
            .error( function(jqXHR, textStatus, errorThrown) {
                console.log("ERROR", errorThrown, textStatus);
                self.formSaveError(true);
                $('#button-save-scenario').attr('disabled', false);
            })
            .complete( function() {
                self.formSaveComplete(true);
            });
        }
  };

  self.toggleScenarioLayer = function(status) {
        layer = app.viewModel.layers.layerIndex[app.scenarioLayerId];

        if (this.selectedFeature()) {
            layer.name = "Scenario: " + this.selectedFeature().name();
        } else {
            layer.name = "Scenario: (empty)";
        }

        if (status == 'off') {
            layer.deactivateLayer();
            layer.url = app.scenarioTileTemplate;
        } else if (status == 'on') {
            layer.activateLayer();
            layer.url = app.scenarioTileTemplate.replace("${scenario_uid}", this.selectedFeature().uid());
        } else {
            if (layer.active()) {
                layer.deactivateLayer();
                layer.url = app.scenarioTileTemplate;
            } else {
                layer.activateLayer();
                layer.url = app.scenarioTileTemplate.replace("${scenario_uid}", this.selectedFeature().uid());
            }
        }

        // always try to bust the cache
        layer.url += "&_=" + String(Math.random() * 1000000);

        if (layer.layer) {
            layer.layer.url = layer.url;
        }
  };
  self.showDeleteDialog = function () {
    $("#scenario-delete-dialog").modal("show");
  };

  self.showDownloadDialog = function () {
    $("#scenario-download-dialog").modal("show");
  };

  self.deleteScenario = function () {
    var url = "/features/generic-links/links/delete/{uid}/".replace("{uid}", self.selectedFeature().uid());
    $('#scenario-delete-dialog').modal('hide');
    $.ajax({
      url: url,
      type: "DELETE",
      success: function (data, textStatus, jqXHR) {
        self.scenarioList.remove(self.selectedFeature());
        self.selectedFeature(false);
        self.showScenarioList(true);
        self.listStart(0);
      }
    });
  };

  // start the scenario editing process
  self.editScenario = function() {
    $('#button-save-scenario').attr('disabled',false);
    self.formLoadError(false);
    self.formLoadComplete(false);
    self.showScenarioForm("edit", self.selectedFeature().uid());
  };

  self.addScenarioStart = function() {
    $('#button-save-scenario').attr('disabled',false);
    self.formLoadError(false);
    self.formLoadComplete(false);
    self.showScenarioForm('create');
  };

  self.cancelAddScenario = function () {
    self.toggleScenarioLayer('off');
    keyboardControl.deactivate();
    self.showScenarioFormPanel(false);
    self.showScenarioList(true);
    self.formSaveError(false);
  };

  self.selectControl = {
      /*
       * Controls the map and display panel 
       * when features are selected
       */
      select: function(feature) {

        var uid = feature.uid();

        var showUrl = app.workspaceUtil.actions.getByRel("self")[0];
        showUrl = showUrl.getUrl([uid]);

        self.reportLoadError(false);
        self.reportLoadComplete(false);
        var jqxhr = $.get(showUrl, function(data) {
          var elem = document.getElementById('scenario-show-container');
          if (elem) {
            ko.cleanNode(elem);
          }
          $('#scenario-show-container').empty().append(data);
          app.viewModel.progress = null;
          clearInterval(app.timer);
          app.timer = null;
          app.viewModel.progress = new progressViewModel();
          ko.applyBindings(app.viewModel.progress, elem);
          app.viewModel.progress.checkTimer();
        })
        .error(function() { self.reportLoadError(true); })
        .complete(function() {
            self.reportLoadComplete(true);
            //self.toggleScenarioLayer('on');
        });
      }
   };

  self.selectScenario = function(feature, event) {
    $('#button-save-scenario').attr('disabled',false);
    if (!self.planningUnitsLoadComplete()) { return false; }

    self.selectControl.select(feature);
    self.selectedFeature(feature);
    bbox = feature.bbox();
    if (js_opts.zoom_on_select && bbox && bbox.length === 4) {
        map.zoomToExtent(bbox);
    }
    self.showScenarioList(false);
  };

  self.selectScenarioById = function (id) {
    var pageSize = self.scenarioList().length / self.listDisplayCount;
    $.each(self.scenarioList(), function (i, feature) {
      if (feature.uid() === id) {
        // set list start to first in list page      
        self.listStart(Math.floor(i / self.listDisplayCount) * self.listDisplayCount);
        self.selectedFeature(this);
      }
    });
  };

  self.loadViewModel = function (data) {
    // load the whole enchilada
    if (data.features && data.features.length) {
        self.scenarioList($.map(data.features, function (feature, i) {
            return ko.mapping.fromJS(feature.properties);
        }));
    } else {
        self.scenarioList.removeAll();
    }
  };

  self.updateScenario = function (data) {
        // Remove it first if it already exists
        var theUid = data.features[0].properties.uid;
        var theScenario = self.getScenarioByUid(theUid);
        if (theScenario) {
            self.scenarioList.remove(theScenario);
        }
          
        self.scenarioList.unshift(ko.mapping.fromJS(data.features[0].properties));
        self.selectedFeature(self.scenarioList()[0]);
  };

  self.loadScenarios = function(scenario_uid) {
    self.scenarioLoadComplete(false);
    self.scenarioLoadError(false);
    var url;
    if (scenario_uid) {
        var jsonLink = app.workspaceUtil.actions.getByTitle("GeoJSON")[0];
        url = jsonLink.getUrl([scenario_uid]);
        handler = function(data) { self.updateScenario(data); };
    } else {
        if (self.dataMode() == 'manage') {
            url = '/seak/scenarios.geojson';
        } else if (self.dataMode() == 'shared') {
            url = '/seak/scenarios_shared.geojson';
        } else {
            console.log("ERROR: dataMode must be either manage or shared");
        }
        handler = function(data) { self.loadViewModel(data); };
    }

    var jqhxr = $.get(url, handler)
    .success( function() {
        if (scenario_uid) {
            var theScenario = self.getScenarioByUid(scenario_uid);
            self.selectScenario(theScenario);
        }
     })
    .error(function() { self.scenarioLoadError(true); })
    .complete(function() {
        self.scenarioLoadComplete(true);
    });
  };

  self.getScenarioByUid = function(uid) {
    var theScenario = false;
    $.each(self.scenarioList(), function(i, scenario) {
        if (scenario.uid() === uid) {
            theScenario = scenario;
            return false;
        }
    });
    return theScenario;
  };

  self.backToScenarioList = function() {
    markers.clearMarkers();
    self.selectedFeature(false);
    self.toggleScenarioLayer('off');
    self.showScenarioList(true);
  };

  self.downloadScenario = function() {
    var uids = [self.selectedFeature().uid()];
    var frm = $('form#download-array-form');
    $(frm).find('input:checkbox').each( function(k,v) {
        if ($(v).attr('checked')) {
            uids.push( $(v).attr('value') );
        }
    });
    var shpTemplate = app.workspaceUtil.actions.getByTitle("Shapefile")[0];
    var shpUrl = shpTemplate.getUrl(uids);
    $('#download-iframe').attr('src', shpUrl);
    $("#scenario-download-dialog").modal("hide");
  };

  self.copyScenario = function() {
    var uids = [self.selectedFeature().uid()];
    var uriTemplate = app.workspaceUtil.actions.getByTitle("Copy")[0];
    var copyURL = uriTemplate.getUrl(uids);
    var jqxhr = $.ajax({
        url: copyURL,
        type: "POST"
    })
    .success( function(data, textStatus, jqXHR) {
        self.selectedFeature(false);
        var d = JSON.parse(data);
        scenario_uid = d["X-Madrona-Select"];
        self.loadScenarios(scenario_uid);
        self.cancelAddScenario(); // Not acutally cancel, just clear 
    })
    .error( function(jqXHR, textStatus, errorThrown) {
        console.log("ERROR", errorThrown, textStatus);
    })
    .complete( function() {
        console.log('copy complete');
    });
    
  };

  self.showShareDialog = function () {
    var uids = [self.selectedFeature().uid()];
    var uriTemplate = app.workspaceUtil.actions.getByTitle("Share")[0];
    var shareURL = uriTemplate.getUrl(uids);
    var jqxhr = $.ajax({
        url: shareURL,
        type: "GET"
    })
    .success( function(data, textStatus, jqXHR) {
        var d = $(data).filter('div');
        $(d).find('div.form_controls').remove();
        $("#share-form-div").empty().append(d);
        $("a.show_members").click(function() {
            var members = $(this).parent().find('ul.member_list');
            if(members.is(':visible')){
                $(this).find('span').text('show members');
            }else{
                $(this).find('span').text('hide members');
            }
            members.toggle(300);
            return false;
        });
    })
    .error( function(jqXHR, textStatus, errorThrown) {
        $("#share-form-div").html("<div id=\"info info-alert\">Could not load share form.</div>");
        console.log("ERROR", errorThrown, textStatus);
    })
    .complete( function() {
        $("#scenario-share-dialog").modal("show");
    });
  };
 
  self.shareScenario = function() {
    var uids = [self.selectedFeature().uid()];
    var uriTemplate = app.workspaceUtil.actions.getByTitle("Share")[0];
    var shareURL = uriTemplate.getUrl(uids);
    var postData = $("form#share").serialize();
    var jqxhr = $.ajax({
        url: shareURL,
        type: "POST",
        data: postData
    })
    .success( function(data, textStatus, jqXHR) {
        var d = JSON.parse(data);
        scenario_uid = d["X-Madrona-Select"];
        self.loadScenarios(scenario_uid);
        self.cancelAddScenario(); // Not acutally cancel, just clear 
    })
    .error( function(jqXHR, textStatus, errorThrown) {
        console.log("ERROR", errorThrown, textStatus);
    })
    .complete( function() {
        $("#scenario-share-dialog").modal("hide");
    });
    
  };
  return self;
}
