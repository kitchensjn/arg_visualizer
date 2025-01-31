require.config({ 
    paths: { 
        d3: 'https://d3js.org/d3.v7.min'
    }
});

require(["d3"], function(d3) {
    /*! @source http://purl.eligrey.com/github/FileSaver.js/blob/master/FileSaver.js */
    
    function download (url, name, opts) {
        var xhr = new XMLHttpRequest()
        xhr.open('GET', url)
        xhr.responseType = 'blob'
        xhr.onload = function () {
            saveAs(xhr.response, name, opts)
        }
        xhr.onerror = function () {
            console.error('could not download file')
        }
        xhr.send()
    }
    
    function corsEnabled (url) {
        var xhr = new XMLHttpRequest()
        // use sync to avoid popup blocker
        xhr.open('HEAD', url, false)
        try {
            xhr.send()
        } catch (e) {}
        return xhr.status >= 200 && xhr.status <= 299
    }
    
    // `a.click()` doesn't work for all browsers (#465)
    function click (node) {
        try {
            node.dispatchEvent(new MouseEvent('click'))
        } catch (e) {
            var evt = document.createEvent('MouseEvents')
            evt.initMouseEvent('click', true, true, window, 0, 0, 0, 80,
                                20, false, false, false, false, 0, null)
            node.dispatchEvent(evt)
        }
    }
    
    function saveAs (blob, name, opts) {
        var URL = URL || webkitURL
        // Namespace is used to prevent conflict w/ Chrome Poper Blocker extension (Issue #561)
        var a = document.createElementNS('http://www.w3.org/1999/xhtml', 'a')
        name = name || blob.name || 'download'

        a.download = name
        a.rel = 'noopener' // tabnabbing

        // TODO: detect chrome extensions & packaged apps
        // a.target = '_blank'

        if (typeof blob === 'string') {
            // Support regular links
            a.href = blob
            if (a.origin !== location.origin) {
            corsEnabled(a.href)
                ? download(blob, name, opts)
                : click(a, a.target = '_blank')
            } else {
            click(a)
            }
        } else {
            // Support blobs
            a.href = URL.createObjectURL(blob)
            setTimeout(function () { URL.revokeObjectURL(a.href) }, 4E4) // 40s
            setTimeout(function () { click(a) }, 0)
        }
    }

    var line = d3.line();
    var step = d3.line().curve(d3.curveStep);
    var stepAfter = d3.line().curve(d3.curveStepAfter);
    var stepBefore = d3.line().curve(d3.curveStepBefore);


    // https://gist.github.com/Rokotyan/0556f8facbaf344507cdc45dc3622177
    // Below are the functions that handle actual exporting:
    // getSVGString ( svgNode ) and svgString2Image( svgString, width, height, format, callback )
    function getSVGString( svgNode ) {
        svgNode.setAttribute('xlink', 'http://www.w3.org/1999/xlink');
        var cssStyleText = getCSSStyles();
        appendCSS( cssStyleText, svgNode );
        var serializer = new XMLSerializer();
        var svgString = serializer.serializeToString(svgNode);
        svgString = svgString.replace(/(\w+)?:?xlink=/g, 'xmlns:xlink='); // Fix root xlink without namespace
        svgString = svgString.replace(/NS\d+:href/g, 'xlink:href'); // Safari NS namespace fix
        return svgString;

        function getCSSStyles() {
            // Extract CSS Rules
            var extractedCSSText = "";
            for (var i = 0; i < document.styleSheets.length; i++) {
                var s = document.styleSheets[i];
                try {
                    if(!s.cssRules) continue;
                } catch( e ) {
                    if(e.name !== 'SecurityError') throw e; // for Firefox
                    continue;
                }
                var cssRules = s.cssRules;
                for (var r = 0; r < cssRules.length; r++) {
                    extractedCSSText += cssRules[r].cssText;
                }
            }
            return extractedCSSText;

        }

        function appendCSS( cssText, element ) {
            var styleElement = document.createElement("style");
            styleElement.setAttribute("type","text/css"); 
            styleElement.innerHTML = cssText;
            var refNode = element.hasChildNodes() ? element.children[0] : null;
            element.insertBefore( styleElement, refNode );
        }
    }


    function svgString2Image( svgString, width, height, format, callback ) {
        var format = format ? format : 'png';
        var imgsrc = 'data:image/svg+xml;base64,'+ btoa( unescape( encodeURIComponent( svgString ) ) ); // Convert SVG string to data URL
        var canvas = document.createElement("canvas");
        var context = canvas.getContext("2d");
        canvas.width = width;
        canvas.height = height;
        var image = new Image();
        image.onload = function() {
            context.clearRect ( 0, 0, width, height);
            context.drawImage(image, 0, 0, width, height);
            canvas.toBlob( function(blob) {
                var filesize = Math.round( blob.length/1024 ) + ' KB';
                if ( callback ) callback( blob, filesize );
            });
        };
        image.src = imgsrc;
    }

    function draw_force_diagram() {
        
        var graph = $data;
        var y_axis = $y_axis;
        var edge_styles = $edges;
        var title = "$title";

        var evenly_distributed_positions = graph.evenly_distributed_positions;

        var tip = d3.select("#arg_${divnum}").append("div")
            .attr("class", "tooltip")
            .style("display", "none");

        var dashboard = d3.select("#arg_${divnum}").append("div").attr("class", "dashboard");
        
        var saving = dashboard.append("button").attr("class", "dashbutton");
        saving.append("svg") //<!--! Font Awesome Free 6.4.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2023 Fonticons, Inc. -->
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("viewBox", "0 0 512 512")
            .append("path")
            .attr("d", "M288 32c0-17.7-14.3-32-32-32s-32 14.3-32 32V274.7l-73.4-73.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l128 128c12.5 12.5 32.8 12.5 45.3 0l128-128c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L288 274.7V32zM64 352c-35.3 0-64 28.7-64 64v32c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V416c0-35.3-28.7-64-64-64H346.5l-45.3 45.3c-25 25-65.5 25-90.5 0L165.5 352H64zm368 56a24 24 0 1 1 0 48 24 24 0 1 1 0-48z");
        var saving_methods = saving.append("span").attr("class", "tip desc");
        var methods = saving_methods.append("div").text("Download As:").append("div").attr("class", "savemethods")
        
        methods.append("button").text("JSON")
            .on("click", function() {
                d3.selectAll("#arg_${divnum} .node").classed("fix", function(d) {
                    d.fx = d.x;
                });
                var textBlob = new Blob(["${source}".replace(/'nodes': .*'links'/, "'nodes': " + JSON.stringify(graph.nodes) + ", 'links'").replaceAll("'", '"')], {type: "text/plain"});
                saveAs(textBlob, "tskit_arg_visualizer.json");
            });
        methods.append("button").text("SVG")
            .on('click', function(){
                var svgString = getSVGString(svg.node());
                var svgBlob = new Blob([svgString], {type:"image/svg+xml;charset=utf-8"});
                saveAs(svgBlob, "tskit_arg_visualizer");
            });
        methods.append("button").text("PNG")
            .on('click', function(){
                var svgString = getSVGString(svg.node());
                svgString2Image(svgString, 2*$width, 2*$height, 'png', save); // passes Blob and filesize String to the callback
            
                function save(dataBlob){
                    saveAs(dataBlob, "tskit_arg_visualizer"); // FileSaver.js function
                }
            });
        
        /*
        methods.append("button").text("HTML")
            .on("click", function(){
                d3.selectAll("#arg_${divnum} .node").classed("fix", function(d) {
                    d.fx = d.x;
                });
                var html = document.querySelector("html").outerHTML;
                var arg_div = document.getElementById("arg_${divnum}").innerHTML;
                console.log(arg_div);
                html = html.replace(arg_div, "");
                html = html.replace("${source}".match(/'nodes': .*'links'/), "'nodes': " + JSON.stringify(graph.nodes) + ", 'links'")
                saveAs(new Blob([html], {type:"text/plain;charset=utf-8"}), "tskit_arg_visualizer.html");
            })
        */

        var reheat = dashboard.append("button").attr("class", "dashbutton activecolor")
            .on("click", function(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();       
                var order = d3.selectAll("#arg_${divnum} .flag1").data().sort((a, b) => d3.ascending(a.x, b.x)).map(a => a.id);;
                d3.selectAll("#arg_${divnum} .node").classed("unfix", function(d) {
                    if ((d.flag != 1) & (d.x_pos_reference == -1)) {
                        delete d.fx;
                    } else {
                        d.fx = evenly_distributed_positions[order.indexOf(d.id)];
                    }
                });
            });
        reheat.append("svg") //<!--! Font Awesome Free 6.4.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2023 Fonticons, Inc. -->
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("viewBox", "0 0 384 512")
            .append("path")
            .attr("d", "M153.6 29.9l16-21.3C173.6 3.2 180 0 186.7 0C198.4 0 208 9.6 208 21.3V43.5c0 13.1 5.4 25.7 14.9 34.7L307.6 159C356.4 205.6 384 270.2 384 337.7C384 434 306 512 209.7 512H192C86 512 0 426 0 320v-3.8c0-48.8 19.4-95.6 53.9-130.1l3.5-3.5c4.2-4.2 10-6.6 16-6.6C85.9 176 96 186.1 96 198.6V288c0 35.3 28.7 64 64 64s64-28.7 64-64v-3.9c0-18-7.2-35.3-19.9-48l-38.6-38.6c-24-24-37.5-56.7-37.5-90.7c0-27.7 9-54.8 25.6-76.9z");
        reheat.append("span").attr("class", "tip desc").text("Reheat Simulation");
        
        if ("$plot_type" == "full") {
            var evenly_distribute = dashboard.append("button").attr("class", "dashbutton activecolor")
                .on("click", function() {
                    var order = d3.selectAll("#arg_${divnum} .flag1").data().sort((a, b) => d3.ascending(a.x, b.x)).map(a => a.id);;
                    d3.selectAll("#arg_${divnum} .flag1").classed("distribute", function(d) {
                        d.fx = evenly_distributed_positions[order.indexOf(d.id)];
                    });
                });
            evenly_distribute.append("svg") //<!--! Font Awesome Free 6.4.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2023 Fonticons, Inc. -->
                .attr("xmlns", "http://www.w3.org/2000/svg")
                .attr("viewBox", "0 0 512 512")
                .append("path")
                .attr("d", "M504.3 273.6c4.9-4.5 7.7-10.9 7.7-17.6s-2.8-13-7.7-17.6l-112-104c-7-6.5-17.2-8.2-25.9-4.4s-14.4 12.5-14.4 22l0 56-192 0 0-56c0-9.5-5.7-18.2-14.4-22s-18.9-2.1-25.9 4.4l-112 104C2.8 243 0 249.3 0 256s2.8 13 7.7 17.6l112 104c7 6.5 17.2 8.2 25.9 4.4s14.4-12.5 14.4-22l0-56 192 0 0 56c0 9.5 5.7 18.2 14.4 22s18.9 2.1 25.9-4.4l112-104z")
            evenly_distribute.append("span").attr("class", "tip desc").text("Space Samples");
        }

        var labelling = dashboard.append("button").attr("class", "dashbutton");
        labelling.append("svg") //<!--! Font Awesome Free 6.4.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2023 Fonticons, Inc. -->
            .attr("xmlns", "http://www.w3.org/2000/svg")
            .attr("viewBox", "0 0 512 512")
            .append("path")
            .attr("d", "M0 80L0 229.5c0 17 6.7 33.3 18.7 45.3l176 176c25 25 65.5 25 90.5 0L418.7 317.3c25-25 25-65.5 0-90.5l-176-176c-12-12-28.3-18.7-45.3-18.7L48 32C21.5 32 0 53.5 0 80zm112 32a32 32 0 1 1 0 64 32 32 0 1 1 0-64z");
        var labelling_methods = labelling.append("span").attr("class", "tip desc");
        var methods = labelling_methods.append("div").text("Node Labels:").append("div").attr("class", "labelmethods")
        
        function switch_node_label(selected) {
            label_text.each(function(d) {
                d3.select(this).selectAll("*").remove();
                if (selected == "default") {
                    multi_line_node_text.call(this, d.label);
                } else if (selected == "id") {
                    multi_line_node_text.call(this, "#" + String(d.id));
                } else {
                    multi_line_node_text.call(this, "");
                }
            })
        }
        
        methods.append("button").attr("class", "node-labels-default").text("DEFAULT")
            .on("click", function() {
                switch_node_label("default");
                // Underline the current selection (could use different highlighting method here)
                d3.selectAll("#arg_${divnum} .labelmethods button").style("text-decoration", "none");
                d3.select(this).style("text-decoration", "underline");
            });
        methods.append("button").attr("class", "node-labels-id").text("#ID")
            .on('click', function(){
                switch_node_label("id");
                // Underline the current selection (could use different highlighting method here)
                d3.selectAll("#arg_${divnum} .labelmethods button").style("text-decoration", "none");
                d3.select(this).style("text-decoration", "underline");
            });
        methods.append("button").attr("class", "node-labels-none").text("NONE")
            .on('click', function(){
                switch_node_label("none");
                // Underline the current selection (could use different highlighting method here)
                d3.selectAll("#arg_${divnum} .labelmethods button").style("text-decoration", "none");
                d3.select(this).style("text-decoration", "underline");
            });


        var svg = d3.select("#arg_${divnum}").append("svg")
            .attr("width", $width)
            .attr("height", $height)
            .style("background-color", "white");

        var result = y_axis.ticks.map(function (x) { 
            return parseInt(x, 10); 
        });

        if (eval(y_axis.include_labels)) {
            var bottom = $height - 50;
            if ($tree_highlighting) {
                bottom = $height - 125;
            }
            var top = 50;
            if (title != "None") {
                top = 100
            }
            var yscale = d3.scaleLinear() 
                .domain([y_axis.max_min[0], y_axis.max_min[1]]) 
                .range([bottom, top]); 

            var y_axis_text = y_axis.text;

            var y_axis = d3.axisRight().scale(yscale)
                .tickValues(result)
                .tickFormat((d, i) => y_axis_text[i]); 

            var y_axis_labels = svg
                .append("g")
                .attr("class", "yaxis")
                .attr("transform", "translate(5,0)")
                .call(y_axis);
        }

        var simulation = d3
            .forceSimulation(graph.nodes)
            .force("link", d3.forceLink()
                .id(function(d) {
                    return d.id;
                })
                .links(graph.links)
            )
            //.force("center", d3.forceCenter(275,250).strength(-10))
            .force("charge", d3.forceManyBody().strength(-100))
            .on("tick", ticked);

        var link_container = svg
            .append("g")
            .attr("class", "links")
            .selectAll("path")
            .data(graph.links)
            .enter()
            .append("g")
            .attr("bounds", function(d) {
                return d.bounds;
            });

        if ((edge_styles.type == "ortho") & eval(edge_styles.include_underlink)) {
            var underlink = link_container
                .append("path")
                .attr("class", "underlink");
        }

        var link = link_container
            .append("path")
            .attr("class", "link")
            .attr("stroke", function(d) {
                return d.stroke;
            });
        
        if (eval(edge_styles.variable_width)) {
            link
                .style("stroke-width", function(d) {
                    return d.region_fraction * 7 + 1;
                });
        }

        if ($tree_highlighting) {
            d3.selectAll("#arg_${divnum} .link")
                .on('mouseover', function (event, d) {
                    d3.select(this)
                        .style('stroke', '#1eebb1')
                        .style("cursor", "pointer");
                    d3.select("#arg_${divnum} .breakpoints")
                        .selectAll(".included")
                            .filter(function(j) {
                                return d.bounds.split(" ").some(function(region) {
                                    region = region.split("-");
                                    return (parseFloat(region[0]) <= j.start) & (parseFloat(region[1]) >= j.stop)
                                });
                            })
                            .style('fill', '#1eebb1');
                })
                .on('mouseout', function (d, i) {
                    d3.select(this)
                        .style('stroke', function(d) {
                            return d.stroke;
                        })
                        .style("cursor", "default")
                    d3.select("#arg_${divnum} .breakpoints").selectAll(".included")
                        .style("fill", d.fill)
                });
        }

        var node_group = svg
            .append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(graph.nodes)
            .enter()
            .append("g");

        var missing_edges = node_group
            .filter(function(d) { return (d.not_included_parents>0) | (d.not_included_children>0); })
            .append("g")
            .attr("class", "missing");

        var missing_parents = missing_edges
            .filter(function(d) { return d.not_included_parents>0; })
            .append("g")
            .attr("class", "parents")
            .append("g");
        var missing_parents_paths = missing_parents.append("path");
        var missing_parents_texts = missing_parents
            .append("text")
                .attr("class", function(d) {
                    return "label"
                })
                .style("fill", "gray")
                .text(function(d) { return d.not_included_parents;});

        var missing_children = missing_edges
            .filter(function(d) { return d.not_included_children>0; })
            .append("g")
            .attr("class", "children")
            .append("g");
        var missing_children_paths = missing_children.append("path");
        var missing_children_texts = missing_children
            .append("text")
                .attr("class", function(d) {
                    return "label"
                })
                .style("fill", "gray")
                .text(function(d) { return d.not_included_children;});

        function multi_line_node_text(text) {
            // Split label text onto separate lines by newline characters, if they exist
            var lines = text.split('\n');
            d3.select(this).selectAll('tspan')
                .data(lines)
                .enter()
                .append('tspan')
                .text(function(line) { return line; })
                .attr('x', 0)
                .attr('y', function(d, i) { 
                    if (lines.length > 1) {
                        // Positioning multiple lines so bottom line is always in the same position
                        return String(i - lines.length + 1) + "em"
                    }
                    return null
                });
        }

        var node = node_group
            .append("path")
            .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; })
            .attr("d", d3.symbol().type(function(d) { return eval(d.symbol); }).size(function(d) { return d.size; }))
            .attr("fill", function(d) { return d.fill; })
            .attr("stroke", function(d) { return d.stroke; })
            .attr("stroke-width", function(d) { return d.stroke_width; })
            .attr("id", function(d) { return String($divnum) + "_node" + d.id; })
            .attr("class", function(d) {
                return "node flag" + d.flag
            })
            .attr("parents", function(d) { return d.child_of.toString().replace(",", " "); })
            .attr("children", function(d) { return d.parent_of.toString().replace(",", " "); })
            .call(
                d3
                    .drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
            )
            .on('mouseover', function (d, i) {
                d3.select(this)
                    .style("cursor", "pointer")
            });

        var mut_symbol = svg
            .append("g")
            .attr("class", "mutations")
            .selectAll("rect")
            .data(graph.mutations)
            .enter()
            .append("g")
            .style("transform-box", "fill-box")
            .style("transform-origin", "center")
            .on("mouseover", function(d, i) {
                d3.select(this)
                    .style("cursor", "pointer")
                    .selectAll("rect")
                        .style("stroke", i.fill);
                d3.select("#arg${divnum}_mut" + i.site_id).style("display", "block");
                var rect = d3.select("#arg_${divnum}").node().getBoundingClientRect();
                tip
                    .style("display", "block")
                    .html("<p style='margin: 0px;'>" + i.content + "</p>")
                    .style("border", i.fill + " solid 2px")
                    .style("left", (d.pageX - rect.x) + "px")
                    .style("top", (d.pageY - rect.y + 25) + "px")
                    .style("transform", "translateX(-50%)");
            })
            .on("mouseout", function(d, i) {
                if (!eval(i.active)) {
                    d3.select(this)
                        .style("cursor", "default")
                        .selectAll("rect")
                            .style("stroke", "#053e4e")
                            .style("fill", i.fill);
                    d3.select("#arg${divnum}_mut" + i.site_id).style("display", "none");
                    tip.style("display", "none");
                }
            });
            
        var mutation_rect_height = 5;
        var mutation_rect_width = 15;
        if ($include_mutation_labels) {
            mutation_rect_height = 15;
            mutation_rect_width = 40;
        }

        var mut_symbol_rect = mut_symbol
            .append("rect")
                .attr("class", "symbol")
                .attr("width", mutation_rect_width)
                .attr("height", mutation_rect_height)
                .attr("fill", function(d) { return d.fill; })
                .attr("stroke", "#053e4e")
                .attr("stroke-width", 2);

        if ($include_mutation_labels) {
            var mut_symbol_label = mut_symbol
                .append("text")
                    .attr("class", "label")
                    .style("font-size", "10px")
                    .attr("text-anchor", "middle")
                    .text(function(d) { return d.label; });
        }

        function rotate_tip(d) {
            if ((d.parent_of.length == 0) & (eval($rotate_tip_labels))) {
                return "translate(-4, 0) rotate(90)"
            }
            return null
        }

        var label = svg
            .append("g")
            .attr("class", "node-labels")
            .selectAll("text")
            .data(graph.nodes)
            .enter()
            //.filter(function(d) { return eval(d.include_label); })
            .append("g");

        var label_text = label
            .attr("class", function(d) {return "label n" + d.id})
            .append("text")
            .each(function(d) {
                return multi_line_node_text.call(this, d.label);
            })
            .attr("transform", rotate_tip);

        function determine_path_type(d) {
            path_type = ""
            var start_position_x = d.source.x;
            var start_position_y = d.source.y;
            var stop_position_x = d.target.x;
            var stop_position_y = d.target.y;
            var vnub = Math.min((stop_position_y-start_position_y)/2, 20);
            if ("y_axis.scale" == "time" | "y_axis.scale" == "log_time") {
                vnub = 0;
            }
            var alt_child = document.getElementById(String($divnum) + "_node" + d.alt_child);
            if (alt_child != null) {
                var alt_child_x = alt_child.getAttribute("cx");
                var alt_child_y = alt_child.getAttribute("cy");
            }
            if (d.source.flag == 131072) {
                path_type += "r0";
                start_position_y = d.source.y + vnub;
            } else {
                if (d.target.y < alt_child_y) {
                    if (d.target.x < d.source.x) {
                        if (d.target.x < d.source.x - 40) {
                            path_type += "tL";
                        } else {
                            path_type += "fL";
                        }
                        start_position_x = d.source.x - 20;
                    } else {
                        if (d.target.x > d.source.x + 40) {
                            path_type += "tR";
                        } else {
                            path_type += "fR";
                        }
                        start_position_x = d.source.x + 20;
                    }
                } else if (d.target.y > alt_child_y) {
                    if (alt_child_x < d.source.x) {
                        if (d.target.x < d.source.x + 40) {
                            path_type += "fR";
                        } else {
                            path_type += "tR";
                        }
                        start_position_x = d.source.x + 20;
                    } else {
                        if (d.target.x > d.source.x - 40) {
                            path_type += "fL";
                        } else {
                            path_type += "tL";
                        }
                        start_position_x = d.source.x - 20;
                    }
                } else {
                    if (d.target.x < alt_child_x) {
                        if (d.target.x < d.source.x - 40) {
                            path_type += "tL";
                        } else {
                            path_type += "fL";
                        }
                        start_position_x = d.source.x - 20;
                    } else if (d.target.x > alt_child_x) {
                        if (d.target.x > d.source.x + 40) {
                            path_type += "tR";
                        } else {
                            path_type += "fR";
                        }
                        start_position_x = d.source.x + 20;
                    } else {
                        if (d.index % 2 == 0) {
                            path_type += "fL";
                            start_position_x = d.source.x - 20;
                        } else {
                            path_type += "fR";
                            start_position_x = d.source.x + 20;
                        }
                    }
                }
            }
            var alt_parent = document.getElementById(String($divnum) + "_node" + d.alt_parent);
            if (alt_parent != null) {
                var alt_parent_x = alt_parent.getAttribute("cx");
                var alt_parent_y = alt_parent.getAttribute("cy");
            }
            if (d.target.flag == 131072) {
                if (d.source.y < alt_parent_y) {
                    if (alt_parent_x < d.target.x) {
                        if (d.source.x < d.target.x + 40) {
                            path_type += "fR";
                        } else {
                            path_type += "tR";
                        }
                        stop_position_x = d.target.x + 20;
                    } else {
                        if (d.source.x > d.target.x - 40) {
                            path_type += "fL";
                        } else {
                            path_type += "tL";
                        }
                        stop_position_x = d.target.x - 20;
                    }
                } else if (d.source.y > alt_parent_y) {
                    if (d.source.x < d.target.x) {
                        if (d.source.x < d.target.x - 40) {
                            path_type += "tL";
                        } else {
                            path_type += "fL";
                        }
                        stop_position_x = d.target.x - 20;
                    } else {
                        if (d.source.x > d.target.x + 40) {
                            path_type += "tR";
                        } else {
                            path_type += "fR";
                        }
                        stop_position_x = d.target.x + 20;
                    }
                } else {
                    if (d.index % 2 == 0) {
                        path_type += "fL";
                        stop_position_x = d.target.x - 20;
                    } else {
                        path_type += "fR";
                        stop_position_x = d.target.x + 20;
                    }
                }
            } else {
                path_type += "b0";
                stop_position_y = d.target.y - vnub;
            }
            if (path_type == "fLb0" ) {
                if (start_position_x >= stop_position_x) {
                    path_type = "tLb0";
                }
            } else if (path_type == "fRb0") {
                if (start_position_x <= stop_position_x) {
                    path_type = "tRb0";
                }
            } else if (path_type == "r0fL") {
                if (start_position_x <= stop_position_x) {
                    path_type = "r0tL";
                }
            } else if (path_type == "r0fR") {
                if (start_position_x >= stop_position_x) {
                    path_type = "r0tR";
                }
            } else if (path_type == "fLfL") {
                if (start_position_x <= stop_position_x) {
                    path_type = "fLtL";
                } else {
                    path_type = "tLfL";
                }
            } else if (path_type == "fRfR") {
                if (start_position_x >= stop_position_x) {
                    path_type = "fRtR";
                } else {
                    path_type = "tRfR";
                }
            }
            return [path_type, start_position_x, start_position_y, stop_position_x, stop_position_y];
        }

        function ortho_pathing(d, path_info) {      
            const path_type = path_info[0];
            const simple_path_type = Array.from(path_type)[0] + Array.from(path_type)[2];
            const start_position_x = path_info[1];
            const start_position_y = path_info[2];
            const stop_position_x = path_info[3];
            const stop_position_y = path_info[4];

            const after_paths = ["rf", "tb", "tf"];
            const before_paths = ["rt", "fb", "ft"];
            const step_paths = ["tt"];
            const mid_paths = ["rb", "ff"];

            if (after_paths.includes(simple_path_type)) {
                return line([[d.source.x, d.source.y],[start_position_x, start_position_y]]) + stepAfter([[start_position_x, start_position_y],[stop_position_x, stop_position_y]]) + line([[stop_position_x, stop_position_y], [d.target.x, d.target.y]]);
            } else if (before_paths.includes(simple_path_type)) {
                return line([[d.source.x, d.source.y],[start_position_x, start_position_y]]) + stepBefore([[start_position_x, start_position_y],[stop_position_x, stop_position_y]]) + line([[stop_position_x, stop_position_y], [d.target.x, d.target.y]]);
            } else if (step_paths.includes(simple_path_type)) {
                return line([[d.source.x, d.source.y],[start_position_x, start_position_y]]) + step([[start_position_x, start_position_y],[stop_position_x, stop_position_y]]) + line([[stop_position_x, stop_position_y], [d.target.x, d.target.y]]);
            } else if (mid_paths.includes(simple_path_type)) {
                return line([[d.source.x, d.source.y],[start_position_x, start_position_y]]) + line([[start_position_x, start_position_y],[start_position_x, start_position_y + (stop_position_y - start_position_y)/2]]) + line([[start_position_x, start_position_y + (stop_position_y - start_position_y)/2],[stop_position_x, start_position_y + (stop_position_y - start_position_y)/2]]) + line([[stop_position_x, start_position_y + (stop_position_y - start_position_y)/2], [stop_position_x, stop_position_y]]) + line([[stop_position_x, stop_position_y], [d.target.x, d.target.y]]);
            }
        }

        function ticked() {

            node
                .attr("transform", function(d) {
                    if (eval(y_axis.include_labels)) {
                        return "translate(" + Math.max(50, Math.min($width-50, d.x)) + "," + d.y + ")";
                    } else {
                        return "translate(" + Math.max(100, Math.min($width-50, d.x)) + "," + d.y + ")";
                    }
                })
                .attr("cx", function(d) {
                    if ((edge_styles.type == "ortho") & (d.x_pos_reference != -1)) {
                        var ref = document.getElementById(String($divnum) + "_node" + d.x_pos_reference);
                        if (ref != null) {
                            d.fx = ref.getAttribute("cx");
                        }
                    }
                    if (eval(y_axis.include_labels)) {
                        return d.x = Math.max(50, Math.min($width-50, d.x));
                    } else {
                        return d.x = Math.max(100, Math.min($width-50, d.x));
                    }
                })
                .attr("cy", function(d) {
                    return d.y;
                });
            
            link_container.each(function(d) {
                var path_info = determine_path_type(d);
                var path = "";
                if (edge_styles.type == "ortho") {
                    path = ortho_pathing(d, path_info);
                } else if (d.source.id == d.alt_parent) {
                    var leftOrRight = 20;
                    if (d.index % 2 == 0) {
                        leftOrRight = -20;
                    }
                    path = "M " + d.source.x + " " + d.source.y + " C " + (d.source.x + leftOrRight).toString() + " " +  (d.source.y - 10).toString() + ", " + (d.target.x + leftOrRight).toString() + " " + (d.target.y + 10).toString() + ", " + d.target.x + " " + d.target.y;
                } else {
                    path = line([[d.source.x, d.source.y], [d.target.x, d.target.y]]);
                }
                if ((edge_styles.type == "ortho") & eval(edge_styles.include_underlink)) {
                    var u = d3.select(this).select(".underlink");
                    u.attr("d", path);
                }
                var l = d3.select(this).select(".link");
                l.attr("path_type", path_info[0]);
                l.attr("d", path);
            })

            mut_symbol
                .attr("transform", function(d) {
                    var parent = document.getElementById(String($divnum) + "_node" + d.source);
                    if (parent != null) {
                        var parent_x = parseFloat(parent.getAttribute("cx"));
                        var parent_y = parseFloat(parent.getAttribute("cy"));
                        var child = document.getElementById(String($divnum) + "_node" + d.target);
                        if (child != null) {
                            var child_x = parseFloat(child.getAttribute("cx"));
                            var child_y = parseFloat(child.getAttribute("cy"));
                            var slope = (parent_y - child_y) / (parent_x - child_x);
                            var intercept = parent_y - slope * parent_x;
                            return "rotate(" + String(-Math.atan((child_x-parent_x)/(child_y-parent_y))*180/Math.PI) + ")";
                        } else {
                            return "rotate(0)";
                        }
                    } else {
                        return "rotate(0)";
                    }
                });

            mut_symbol_rect
                .attr("x", function(d) {
                    var parent = document.getElementById(String($divnum) + "_node" + d.source);
                    if (parent != null) {
                        var parent_x = parseFloat(parent.getAttribute("cx"));
                        var parent_y = parseFloat(parent.getAttribute("cy"));
                        var child = document.getElementById(String($divnum) + "_node" + d.target);
                        if (child != null) {
                            var child_x = parseFloat(child.getAttribute("cx"));
                            var child_y = parseFloat(child.getAttribute("cy"));
                            if (parent_x - child_x == 0) {
                                return parent_x - mutation_rect_width/2;
                            } else {
                                var slope = (parent_y - child_y) / (parent_x - child_x);
                                var intercept = parent_y - slope * parent_x;
                                return ((d.y - intercept) / slope) - mutation_rect_width/2;
                            }
                        } else {
                            return 0;
                        }
                    } else {
                        return 0;
                    }
                })
                .attr("y", function(d) { return d.y - mutation_rect_height/2; });
            
            if ($include_mutation_labels) {
                mut_symbol_label
                    .attr("transform", function(d) {
                        var y = d.y+3.5;
                        var x = 0;
                        var parent = document.getElementById(String($divnum) + "_node" + d.source);
                        if (parent != null) {
                            var parent_x = parseFloat(parent.getAttribute("cx"));
                            var parent_y = parseFloat(parent.getAttribute("cy"));
                            var child = document.getElementById(String($divnum) + "_node" + d.target);
                            if (child != null) {
                                var child_x = parseFloat(child.getAttribute("cx"));
                                var child_y = parseFloat(child.getAttribute("cy"));
                                if (parent_x - child_x == 0) {
                                    x = parent_x;
                                } else {
                                    var slope = (parent_y - child_y) / (parent_x - child_x);
                                    var intercept = parent_y - slope * parent_x;
                                    x = ((d.y - intercept) / slope);
                                }
                            } else {
                                x = 0;
                            }
                        } else {
                            x = 0;
                        }
                        return "translate(" + String(x) + "," + String(y) + ")";
                    });
            }

            function determine_label_positioning(d) {
                if (d.flag == 131072 || d.parent_of.length == 0 || d.child_of.length == 0) {
                    return "c";
                } else if (d.child_of.length == 1) {
                    var parent = document.getElementById(String($divnum) + "_node" + d.child_of[0])
                    if (parent != null) {
                        var parent_x = parent.getAttribute("cx");
                        if (parent_x > d.x+1) {
                            return "l";
                        } else {
                            return "r";
                        }
                    } else {
                        return "r";
                    }
                } else {
                    return "r";
                }
            };

            label
                .each(function(d) {
                    var l = d3.select(this);
                    var positioning = determine_label_positioning(d);
                    var x = d.x;
                    var anchor = "middle";
                    // Find offsets from CSS
                    const cstyle = getComputedStyle(this)
                    const symbolSize = Math.sqrt(d.size);
                    const cssOffset = cstyle.getPropertyValue('--offset');
                    // default should depend on the symbol size (which is square pixels) and the font size
                    const offset = cssOffset ? parseInt(cssOffset) : symbolSize/2 + parseFloat(cstyle.fontSize)/2;
                    const cssTipoffset = cstyle.getPropertyValue('--tipoffset');
                    // default of 25 if not set: perhaps should be related to the tip symbol size?
                    const tipoffset = cssTipoffset ? parseInt(cssTipoffset) : symbolSize/2 + parseFloat(cstyle.fontSize);
                    if (positioning == "l") {
                        x = d.x - offset;
                        anchor = "end";
                    } else if (positioning == "r") {
                        x = d.x + offset;
                        anchor = "start";
                    }
                    l.attr("text-anchor", anchor);
                    l.attr("transform", function(d) {
                        // adding slightly more spacing in the y-axis when positioning is middle (c)
                        var y = d.y - offset;
                        if (positioning == "c") {
                            y = y - 3;
                        }
                        if (d.parent_of.length == 0) {
                            y = d.y + tipoffset;
                            if (positioning == "c") {
                                y = y + 3;
                            }
                        }
                        // only bother showing up to 4 d.p.
                        return "translate(" + parseFloat(x.toFixed(4)) + "," + parseFloat(y.toFixed(4)) + ")";
                    })
                });

            missing_parents_paths
                .each(function(d) {
                    var l = d3.select(this);
                    l.style("stroke-width", "4px");
                    l.style("stroke-dasharray", "5");
                    l.style("stroke", "gray");
                    l.attr("d", line([[d.x, d.y], [d.x, d.y-30]]));
                });
            
            missing_parents_texts
                .each(function(d) {
                    var l = d3.select(this);
                    l.attr("text-anchor", "middle");
                    l.attr("x", d.x);
                    l.attr("y", d.y-30);
                });

            missing_children_paths
                .each(function(d) {
                    var l = d3.select(this);
                    l.style("stroke-width", "4px");
                    l.style("stroke-dasharray", "5");
                    l.style("stroke", "gray");
                    l.attr("d", line([[d.x, d.y], [d.x, d.y+30]]));
                });
            
            missing_children_texts
                .each(function(d) {
                    var l = d3.select(this);
                    l.attr("text-anchor", "middle");
                    l.attr("x", d.x);
                    l.attr("y", d.y+40);
                });
        }

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d3.selectAll("#arg_${divnum} .node").classed("ref", function(j) {
                if ((edge_styles.type == "ortho") & (j.id == d.x_pos_reference)) {
                    j.fx = d.x;
                }
            });
        }

        function dragged(event, d) {
            d.fx = event.x;
            d3.selectAll("#arg_${divnum} .node").classed("ref", function(j) {
                if ((edge_styles.type == "ortho") & (j.id == d.x_pos_reference)) {
                    j.fx = event.x;
                }
            });
        }

        if ($tree_highlighting) {
            
            var th_group = svg.append("g").attr("class", "tree_highlighting");
            
            th_group
                .append("g")
                .attr("class", "breakpoints")
                .selectAll("rect")
                .data(graph.breakpoints)
                .enter()
                .append("rect")
                .attr("class", function(d) {
                    if (eval(d.included)) {
                        return "included";
                    }
                })
                .attr("start", function(d) {
                    return d.start;
                })
                .attr("stop", function(d) {
                    return d.stop;
                })
                .attr("x", function(d) {
                    return d.x_pos;
                })
                .attr("y", $height-60)
                .attr("width", function(d) {
                    return d.width;
                })
                .attr("height", 40)
                .attr("stroke", "#FFFFFF")
                .attr("stroke-width", 1)
                .attr("fill", function(d) {
                    if (eval(d.included)) {
                        return d.fill;
                    } else {
                        return "gray";
                    }
                })
                .on('mouseover', function (event, d) {
                    if (eval(d.included)) {
                        d3.select(this)
                            .style('fill', '#1eebb1')
                            .style("cursor", "pointer");
                        var highlight_links = d3.select("#arg_${divnum} .links")
                            .selectAll("g")
                                .filter(function(j) {
                                    return j.bounds.split(" ").some(function(region) {
                                        region = region.split("-");
                                        return (parseFloat(region[1]) > d.start) & (parseFloat(region[0]) < d.stop)
                                    });
                                });
                        highlight_links.raise();
                        highlight_links
                            .select(".link")
                            .style("stroke", "#1eebb1");
                    }
                })
                .on('mouseout', function (event, d) {
                    if (eval(d.included)) {
                        d3.select(this)
                            .style('fill', d.fill)
                            .style("cursor", "default");
                        d3.selectAll("#arg_${divnum} .link")
                            .style("stroke", function(d) {
                                return d.stroke;
                            });
                    }
                });
            
            var endpoints = th_group.append("g").attr("class", "endpoints");
            
            endpoints
                .append("text")
                    .attr("class", "label")
                    .style("text-anchor", "start")
                    .text(graph.breakpoints[0].start)
                    .attr("x", graph.breakpoints[0].x_pos)
                    .attr("y", $height-5);
            
            endpoints
                .append("text")
                    .attr("class", "label")
                    .style("text-anchor", "end")
                    .text(graph.breakpoints[graph.breakpoints.length-1].stop)
                    .attr("x", $width)
                    .attr("y", $height-5);

            var mut_pos = th_group
                .append("g")
                .attr("class", "mutations")
                .selectAll("line")
                .data(graph.mutations)
                .enter()
                .append("g")
                .attr("id", function(d) { return "arg" + String($divnum) + "_mut" + d.site_id; })
                .style("display", "none");
        
            mut_pos
                .each(function(d) {
                    if (typeof(d.x_pos) == "object") {
                        d3.select(this).selectAll("line").data(d.x_pos)
                            .enter()
                            .append("line")
                            .attr("x1", function(x) { return x; })
                            .attr("y1", $height-60-5)
                            .attr("x2", function(x) { return x; })
                            .attr("y2", $height-60+40+5)
                            .style("stroke-width", 3)
                            .style("stroke", d.fill)
                            .style("fill", "none");
                    } else {
                        d3.select(this)
                            .append("line")
                            .attr("x1", d.x_pos)
                            .attr("y1", $height-60-5)
                            .attr("x2", d.x_pos)
                            .attr("y2", $height-60+40+5)
                            .style("stroke-width", 3)
                            .style("stroke", d.fill)
                            .style("fill", "none");
                    }
                });
            
            /*
            var mut_text = mut_pos
                .append("text")
                .attr("text-anchor", function(d) {
                    if (d.x_pos > ($width*9/10)) {
                        return "end";
                    } else if (d.x_pos < $width*1/10) {
                        return "start";
                    } else {
                        return "middle";
                    }
                })
                .style("font-size", "10px")
                .style("font-family", "Arial")
                .attr("fill", function(d) { return d.fill; })
                .attr("transform", function(d) {
                    return "translate(" + String(d.x_pos) + "," + String($height-60-10) + ")";
                });
        
            mut_text
                .text(function(d) {
                    if ($include_mutation_labels) {
                        return String(d.site_id) + ":" + String(d.position);
                    } else {
                        return d.label;
                    }
                });
            */
        }

        if (title != "None") {
            svg.append("text")
                .attr("class", "label")
                .text(title)
                .style("font-size", "20px")
                .attr("x", $width / 2)
                .style("transform", "translate(-50%, 50%)")
                .attr("y", 30);
        }
    }

    draw_force_diagram()
})