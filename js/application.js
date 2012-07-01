$(function(){

    var current_size = 0;
    $('.size_btn li a').click(function(){
        var clicked_li = $(this).parent();
        clicked_li.siblings().removeClass('active');
        clicked_li.addClass('active');
        current_size = $(this).data('size');
    });

    $('.add_to_cart').click(function(){
        var qty = $('#qty_input').val();
        if (isNaN(parseInt(qty)) || parseInt(qty) == 0) { 
            alert("Please add a valid quantity");
            return false; 
        }
        var queryString = "tshirt_id=" + $('.main_img').data('tshirt_id') + 
                    "&qty=" + qty + "&size=" + current_size + 
                    "&item_title=" + $.trim($('.product_title').text());
        
        $.getJSON('/cart/add', queryString, function(data){
            if (data["status"] == 1) {
                var newcount = parseInt($.trim($('.itemCount').text())) + parseInt(qty);
                $('.itemCount').text(newcount);
            }
            $('#addition_details').html(data["msg"]);
            console.log(data["msg"]);
        });
        return false;
    });

    // Compiling Handlebars templates

    var source = $("#item_template").html();
    var template = Handlebars.compile(source);

    $('.template_trigger').click(function(){
        $.get('/all.json', function(data){
            $.each(data, function(i, val) {
                var context = { id: val["id"], title: val["title"] }
                var html = template(context);
                $('#top').append(html);
            });
        });
    });
});
