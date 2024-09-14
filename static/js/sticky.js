(function ($) {
    // Auto-grow textareas function
    $.fn.autogrow = function () {
        return this.filter('textarea').each(function () {
            var $self = $(this);
            var minHeight = $self.height();
            var noFlickerPad = $self.hasClass('autogrow-short') ? 0 : parseInt($self.css('line-height'), 10) || 0;

            var shadow = $('<div></div>').css({
                position: 'absolute',
                top: -10000,
                left: -10000,
                width: $self.width(),
                fontSize: $self.css('font-size'),
                fontFamily: $self.css('font-family'),
                fontWeight: $self.css('font-weight'),
                lineHeight: $self.css('line-height'),
                resize: 'none',
                wordWrap: 'break-word',
                whiteSpace: 'pre-wrap',
                padding: $self.css('padding'),
                border: $self.css('border')
            }).appendTo(document.body);

            var update = function () {
                var val = $self.val()
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/&/g, '&amp;')
                    .replace(/\n$/g, '<br/>&nbsp;')
                    .replace(/\n/g, '<br/>')
                    .replace(/ {2,}/g, function (space) {
                        return '&nbsp;'.repeat(space.length - 1) + ' ';
                    });

                shadow.css('width', $self.width());
                shadow.html(val + (noFlickerPad === 0 ? '' : '&nbsp;'));
                $self.height(Math.max(shadow.height() + noFlickerPad, minHeight));
            };

            $self.on('input', update);
            $(window).on('resize', update);
            update();
        });
    };
})(jQuery);

const noteTemplate = `
    <div class="note" data-id="">
        <a href="javascript:;" class="button remove">X</a>
        <div class="note_cnt">
            <textarea class="title" placeholder="Enter note title"></textarea>
            <textarea class="cnt" placeholder="Enter note description here"></textarea>
        </div>
    </div>`;

let noteZindex = 1;
const API_URL = '/sticky-notes'; // Replace with your server URL

async function fetchStickyNotes() {
    try {
        const response = await fetch(API_URL);
        const notes = await response.json();
        for (const [id, note] of Object.entries(notes)) {
            const noteElement = $(noteTemplate).hide().appendTo("#board").show("fade", 300).draggable({
                start: function () {
                    $(this).css('z-index', ++noteZindex);
                }
            }).attr('data-id', id);

            noteElement.find('.title').val(note.title || '');
            noteElement.find('.cnt').val(note.content || '');
        }
        $('.remove').off('click').on('click', deleteNote);
        $('textarea').autogrow();
    } catch (error) {
        console.error('Error fetching sticky notes:', error);
    }
}

async function saveNoteToFirebase(noteElement) {
    const id = noteElement.attr('data-id');
    const title = noteElement.find('.title').val();
    const content = noteElement.find('.cnt').val();
    const noteData = { title, content };

    try {
        if (id) {
            // Update existing note
            await fetch(`${API_URL}/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(noteData)
            });
        } else {
            // Create new note
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(noteData)
            });
            const data = await response.json();
            noteElement.attr('data-id', data.id);
        }
    } catch (error) {
        console.error('Error saving sticky note:', error);
    }
}

async function deleteNote() {
    const noteElement = $(this).closest('.note');
    const id = noteElement.attr('data-id');

    try {
        if (id) {
            await fetch(`${API_URL}/${id}`, {
                method: 'DELETE'
            });
        }
        noteElement.hide("puff", { percent: 133 }, 250, function () {
            $(this).remove();
        });
    } catch (error) {
        console.error('Error deleting sticky note:', error);
    }
}

function newNote() {
    const noteElement = $(noteTemplate).hide().appendTo("#board").show("fade", 300).draggable({
        start: function () {
            $(this).css('z-index', ++noteZindex);
        }
    });

    $('.remove').off('click').on('click', deleteNote);
    $('textarea').autogrow();

    noteElement.find('textarea').on('input', function () {
        saveNoteToFirebase($(this).closest('.note'));
    });
}

$(document).ready(function () {
    $("#board").css('height', $(document).height());

    $("#add_new").on('click', newNote);

    fetchStickyNotes();
});
