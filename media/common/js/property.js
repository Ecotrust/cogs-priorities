function propertiesViewModel () {
  var self = this;
  // TODO: make function to map properties with test  
  self.showPropertyPanels = ko.observable(true);
  self.propertyList = ko.observableArray();
  self.showEditPanel = ko.observable(false);
  self.showDetailPanel = ko.observable(false);
  self.showCreatePanel = ko.observable(false);
  self.showDrawHelpPanel = ko.observable(false);
  self.drawingActivated = ko.observable(false);
  self.preventUpdates = ko.observable(false);
  self.showPropertyList = ko.observable(true);
  self.showNoPropertiesHelp = ko.observable(true);
  self.selectedProperty = ko.observable();
  self.actionPanelType = ko.observable(false);
  self.selectProperty = function (property, event, zoomTo) {
    var bbox = OpenLayers.Bounds.fromArray(property.bbox());
    // TODO: Make active!
    if (! self.preventUpdates()) {
      if (event) {     
        $(event.target).closest('tr')
          // .addClass('active')
          // .siblings().removeClass('active');         
          app.selectFeature.unselectAll();
          app.selectFeature.select(property.feature);
      } 
      // set the selected property for the viewmodel
      self.selectedProperty(property);
      self.showDetailPanel(true);
      // zoom the map to the selected property
      // map.zoomToExtent(bounds);
      if (zoomTo) {
        if (map.getZoomForExtent(bbox) - map.zoom > 1) {
          map.panTo(bbox.getCenterLonLat());
        } else {
          map.zoomToExtent(bbox);        
        }
      }
    }

  };

  self.selectPropertyByUID = function (uid, zoomTo) {
    $.each(self.propertyList(), function (i, property) {
      if (property.uid() === uid) {
        self.selectProperty(property, null, zoomTo);
      }
    });
  };

  self.zoomToExtent = function () {
    map.zoomToExtent(app.property_layer.getDataExtent());
  }

  self.cleanupForm = function ($form) {
    // remove the submit button, strip out the geometry
    $form
      .find('input:submit').remove().end()
      .find('#id_geometry_final').closest('.field').remove();

    // put the form in a well and focus the first field
    $form.addClass('well');
    $form.find('.field').each(function () {
      var $this = $(this);
      // add the bootstrap classes
      $this.addClass('control-group');
      $this.find('label').addClass('control-label');
      $this.find('input').wrap($('<div/>', { "class": "controls"}));
      $this.find('.controls').append($('<p/>', { "class": "help-block"}));

    });
    $form.find('input:visible').first().focus();
    
  }

  self.showEditForm = function () {
    var formUrl = '/features/forestproperty/{uid}/form/'.replace('{uid}', this.selectedProperty().uid());
    $.get(formUrl, function (data) {
      var $form = $(data).find('form');
        
      self.cleanupForm($form);
      // show the form in the panel
      self.showDetailPanel(false);
      self.showEditPanel(true);
      self.preventUpdates(true);
      $('#edit-panel').empty().append($form);
      $form.find('input:visible:first').focus();

      $form.bind('submit', function (event) {
        event.preventDefault();
        self.updateFeature(self, event);
      });

      app.modifyFeature.selectFeature(self.selectedProperty().feature);
      app.modifyFeature.activate();
      self.showPropertyList(false)

    })
  };
  self.startAddDrawing = function () {
    self.showDetailPanel(false);
    self.showDrawHelpPanel(true);
    self.drawingActivated(true);
    self.showNoPropertiesHelp(false);
    self.preventUpdates(true);
    app.drawFeature.activate();
    self.showPropertyList(false)
  };
  self.showAddForm = function () {
    var formUrl = '/features/forestproperty/form/';

    $.get(formUrl, function (data) {
      var $form = $(data).find('form');
      
      self.cleanupForm($form);
      
      // show the form in a modal
      self.showDetailPanel(false);
      self.showCreatePanel(true);
      $('#create-panel').empty().append($form);
      $form.find('input:visible:first').focus();
       $form.bind('submit', function (event) {
        event.preventDefault();
        self.addFeature(self, event);
      });
    })
  };

  self.addFeature = function (self, event) {
    self.saveFeature(event, null, app.newGeometry);
    
  };

  app.saveFeature = function (f) {
    app.newGeometry = f.geometry.toString();
    self.showAddForm();
  };


  self.updateFeature = function (self, event) {
    var geometry = app.modifyFeature.feature.geometry.toString();
    self.saveFeature(event, self.selectedProperty(), geometry);
  };

  self.saveFeature = function (event, property, geometry) {
    var $dialog = $(event.target).closest('.form-panel'),
      $form = $dialog.find('form'), 
      actionUrl = $form.attr('action'),
      values = {}, error=false;
    $form.find('input').each(function () {
      var $input = $(this);
      if ($input.closest('.field').hasClass('required') && $input.attr('type') !== 'hidden' && ! $input.val()) {
        error = true;
        $input.closest('.control-group').addClass('error');
        $input.siblings('p.help-block').text('This field is required.');
      } else {
        values[$input.attr('name')] = $input.val();
      }
    });
    if (error) {
      return false;
    }
    values.geometry_final = geometry;
    $form.addClass('form-horizontal')
    self.showEditPanel(false);
    self.showCreatePanel(false);
    self.preventUpdates(false);
    $.ajax({
      url: actionUrl,
      type: "POST",
      data: values,
      success: function (data, textStatus, jqXHR) {
        // property is not defined if new
        self.updateOrCreateProperty(JSON.parse(data), property);
        self.showPropertyList(true);
        app.drawFeature.deactivate();
        app.modifyFeature.deactivate();
        self.showNoPropertiesHelp(false);
        app.new_features.removeAllFeatures()

      },
      error: function (jqXHR, textStatus, errorThrown) {
        self.cancelEdit(self);
      }
    });
  };

  self.updateOrCreateProperty = function (data, property) {
    var updateUrl = '/features/generic-links/links/geojson/{uid}/'.replace('{uid}', data["X-Madrona-Select"]);
    $.get(updateUrl, function (data) {
      var newPropertyVM, newProperty = data.features[0].properties;
      if (property) {
        // updating existing property
        ko.mapping.fromJS(newProperty, property);
        self.selectProperty(property);
      } else {
        // add a new property
        self.selectPropertyByUID(data.features[0].uid)
        app.property_layer.addFeatures(app.geojson_format.read(data));
      }
    });
  };
  self.showDeleteDialog = function () {
    $("#delete-dialog").modal("show");
  };

  self.deleteFeature = function () {
    var url = "/features/generic-links/links/delete/{uid}/".replace("{uid}", self.selectedProperty().uid());
    $('#delete-dialog').modal('hide');
    self.showEditPanel(false);
    self.showCreatePanel(false);
    self.showDetailPanel(true);
    self.preventUpdates(false);
    $.ajax({
      url: url,
      type: "DELETE",
      success: function (data, textStatus, jqXHR) {
        app.modifyFeature.deactivate();
        app.property_layer.removeFeatures(self.selectedProperty().feature);
        self.propertyList.remove(self.selectedProperty());
        if (self.propertyList().length) {
          self.selectProperty(self.propertyList()[0]);
         $("#properties-list tbody").find('tr').first().not(':only-child').addClass('active');
        } else {
          self.showDetailPanel(false);
          self.showNoPropertiesHelp(true);
        }
      }
    });
  };

  self.closeDialog = function (self, event) {
     $(event.target).closest(".modal").modal("hide");
  };

  self.cancelEdit = function (self, event) {
    self.showEditPanel(false);
    self.showCreatePanel(false);
    self.showDrawHelpPanel(false);
    self.preventUpdates(false);
    self.showNoPropertiesHelp(self.propertyList().length ? false: true);
    app.modifyFeature.resetVertices();
    app.modifyFeature.deactivate();
    app.drawFeature.deactivate();
    self.showDetailPanel(self.propertyList().length ? true: false);
    app.new_features.removeAllFeatures();
    self.showPropertyList(true);

  };

  self.manageStands = function (self, event) {
    // create active property layer
    // copy active property to new layer
    // hide other properties
    app.property_layer.setOpacity(.4);
    // initialize stand manager
    if (app.stands.viewModel) {
      app.stands.viewModel.reloadStands(self.selectedProperty());
    } else {
      app.stands.viewModel = new standsViewModel();
      app.stands.viewModel.initialize(self.selectedProperty());
    }

    // hide property panels
    app.stands.viewModel.showStandPanels(true);
    self.showPropertyPanels(false);
  }
  
  // initialize properties and vm
  // return request object to apply bindings when done
  self.init = function () {
    return $.get('/trees/user_property_list/', function (data) {
      app.bounds = OpenLayers.Bounds.fromArray(data.features.length >0 ? data.bbox: 
        [-13954802.50397, 5681411.4375898, -13527672.389972, 5939462.8450446]);
      map.zoomToExtent(app.bounds);
      // bind event to selected feature
      app.properties.featureAdded = function(feature) { 
        app.drawFeature.deactivate();
        self.showDrawHelpPanel(false);
        app.saveFeature(feature);
      };
      app.drawFeature.featureAdded = app.properties.featureAdded;

      app.property_layer.events.on({
        'featureselected': function (feature) {
          self.selectPropertyByUID(feature.feature.data.uid, true);
        },
        'featureadded': function (feature) {
          var featureViewModel = ko.mapping.fromJS(feature.feature.data);
          // save a reference to the feature
          featureViewModel.feature = feature.feature;
          // add it to the viewmodel
          self.propertyList.unshift(featureViewModel);
        },
        'featuresadded': function (data) {
          // if only adding one layer, select and zoom
          // otherwise just select the last one and zoom to the full extent of the layer
          self.showNoPropertiesHelp(false);
          if (data.features.length === 1) {
            self.selectPropertyByUID(data.features[0].data.uid, true);
          } else {
            self.selectPropertyByUID(data.features[data.features.length-1].data.uid, false);                
            map.zoomToExtent(app.bounds);         
          }
        }
      });
  
      // set up the breadcrumbs    
      app.breadCrumbs.breadcrumbs.push({url: '/', name: 'Home', action: null});

      app.breadCrumbs.breadcrumbs.push({name: 'Properties', url: '/properties', action: null})
      
      // select the first property and show the detail panel
      if (data.features.length) {
        app.property_layer.addFeatures(app.geojson_format.read(data));
        //self.selectedProperty(self.propertyList()[0]);
        //self.showDetailPanel(true);   
      }
    });  
  }

  
};
