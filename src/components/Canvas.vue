<template>
    <div
        ref='cnv'
        class="cnv section columns is-multiline"
        tabindex="-1"
        @keyup.left="prev_image"
        @keyup.81="prev_image"
        @keyup.right="next_image"
        @keyup.69="next_image"
        @keyup.83="post_annotations"
    >
        <div
            v-if="img_id_short"
            class="image_id"
        >
            <small>ID: {{ img_id_short }}</small>
        </div>
        <div
            class="center column is-full"
            id="control-panel"
        >
            <div class="columns is-centered is-multiline">
                <div class="column is-2">
                    <h4 class="title is-5 has-text-centered">
                        Image {{ this.sequential_counter + 1 }} / {{ this.images.length }}
                    </h4>
                </div>
                <div class="column is-1"><button
                        class="button is-info"
                        id="btn-previous"
                        @click="prev_image"
                    >
                        <b-icon
                            pack="fas"
                            icon="chevron-left"
                        > </b-icon> <span>Prev. (Q)</span>
                    </button> </div>
                <div class="column is-1"><button
                        class="button is-info"
                        id="btn-next"
                        @click="next_image"
                    >
                        <span>Next (E)</span>
                        <b-icon
                            pack="fas"
                            icon="chevron-right"
                        > </b-icon>
                    </button>
                </div>
                <!-- <div class="column is-6"><button class="button is-info" id="btn-undo">       <b-icon pack="fas" icon="undo">        </b-icon> <span>Undo (Z)</span>     </button>   </div>
                    <div class="column is-6"><button class="button is-info" id="btn-redo">       <b-icon pack="fas" icon="redo">        </b-icon> <span>Redo (X)</span>     </button>   </div> -->
                <!-- <div class="column is-6 is-offset-3"><button class="button is-info" id="btn-brush"> <b-icon pack="fas" icon="brush">       </b-icon> <span>Brush</span>    </button>   </div> -->
                <div class="column is-1">
                    <button
                        class="button is-success"
                        id="btn-sync"
                        @click="post_annotations"
                    >
                        <b-icon
                            pack="fas"
                            icon="sync"
                        ></b-icon>
                        <span>Sync (S)</span>
                    </button>
                </div>
                <div class="column is-1">
                    <div class="columns" style="margin-bottom: 0;">
                        <div class="column">
                            <button
                                class="button is-info"
                                id="btn-brush-dec"
                                @click="canvas_brush_dec"
                            >
                                <b-icon
                                    pack="fas"
                                    icon="minus"
                                ></b-icon>
                            </button>
                        </div>
                        <div class="column is-half">
                            <button
                                class="button is-info"
                                id="btn-brush-inc"
                                @click="canvas_brush_inc"
                            >
                                <b-icon
                                    pack="fas"
                                    icon="plus"
                                ></b-icon>
                            </button>
                        </div>
                    </div>
                    <span>Brush size</span>
                    <span class="right">{{ this.brush_size }}</span>
                </div>
                <div class="column is-1">
                    <button
                        class="button is-danger"
                        id="btn-eraser"
                        @click="canvas_clear"
                    >
                        <b-icon
                            pack="fas"
                            icon="eraser"
                        ></b-icon>
                        <span>Clear</span>
                    </button>
                </div>
                <!-- <div class="column is-6 is-offset-3"><hr><button class="button is-success" id="btn-save" @click="export_annotation"> <b-icon pack="fas" icon="save">            </b-icon> <span>Export</span>    </button>   </div> -->
            </div>
        </div>
        <div class="column is-full">
            <div class="columns is-multiline is-centered">
                <div class="column canvas-container-wrapper">
                    <h5 class="title is-5 has-text-centered">Reference image</h5>
                    <canvas
                        class="app-canvas"
                        id="vis-canvas"
                        ref="vis-canvas"
                    />
                </div>
                <div class="column canvas-container-wrapper">
                    <h5 class="title is-5 has-text-centered">Annotation canvas</h5>
                    <canvas
                        class="app-canvas"
                        id="main-canvas"
                        ref="main-canvas"
                    />
                </div>
                <div class="column hidden">
                    <canvas
                        class="hidden"
                        id="export-canvas"
                        ref="export-canvas"
                    ></canvas>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { fabric } from 'fabric'
import { mapState } from 'vuex'
import * as Sentry from '@sentry/browser';

export default {
    name: 'Canvas',
    props: {},
    data() {
        return {
            // the CanvasRenderingContext to turn canvas into a reactive component:
            paths_group: new fabric.Group(),
            brush_size: 4,
            context: null,
            image: null,
        }
    },
    computed: {
        ...mapState('images', [
            'annotations',
            'canvas_image',
            'images',
            'sequential_counter',
        ]),
        img_id_short() {
            if (this.canvas_image && this.canvas_image.img_id) {
                return this.canvas_image.img_id.substr(this.canvas_image.img_id.length - 10)
            }
            return undefined
        },
        comp_annotations() {
            return this.annotations
        },
    },
    methods: {

        canvas_brush_dec() {
            if (this.brush_size <= 1) {
                return
            }
            this.brush_size--;
            this.canvas.main_canvas.freeDrawingBrush.width = this.brush_size * 5;
        },

        canvas_brush_inc() {
            if (this.brush_size >= 6) {
                return
            }
            this.brush_size++;
            this.canvas.main_canvas.freeDrawingBrush.width = this.brush_size * 5;
        },

        prev_image: function () {
            let next_action = 'images/decSeqCounter'
            if (this.sequential_counter == undefined || this.sequential_counter <= 0) {
                next_action = undefined
            }
            this.export_annotation(next_action)
        },

        next_image: function () {
            if (this.sequential_counter == undefined) {
                return
            }
            let next_action = 'images/incSeqCounter'
            if (this.sequential_counter >= this.images.length - 1) {
                this.$router.push({ name: 'thankyou' })
                next_action = undefined
            }
            this.export_annotation(next_action)
        },

        post_annotations: function () {
            this.$store.dispatch('images/postAnnotations')
        },

        canvas_clear: function () {
            this.canvas.main_canvas.getObjects().map(o => {
                this.canvas.main_canvas.remove(o)
            })
        },

        export_annotation: function (next_action) {

            // other useful methods:
            // console.log(this.canvas.main_canvas.toSVG())
            // console.log(this.canvas.main_canvas.toObject())

            // clone objects from main-canvas, as we cannot directly
            // export tainted canvases due to security constraints
            const objs = this.canvas.main_canvas.getObjects()
            if (objs.length === 0) {
                next_action && this.$store.dispatch(next_action)
                return  // empty canvas, stop function
            }

            console.log(' > Exporting annotation');
            objs.map(o => this.canvas.export_canvas.add(o))
            this.canvas.export_canvas.renderAll()

            // convert canvas to image
            this.$refs['export-canvas'].toBlob(blob => {

                // now objects can be removed from export canvas
                this.canvas.export_canvas.getObjects().map(o => {
                    this.canvas.export_canvas.remove(o)
                })

                // display generated image (optional)
                // const new_img = document.createElement('img'),
                //     url = URL.createObjectURL(blob);
                // new_img.onload = function() {
                //     URL.revokeObjectURL(url);
                // };
                // new_img.src = url;
                // document.body.appendChild(new_img);

                // convert blob to base64 for later upload
                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = () => {
                    const base64data = reader.result;
                    const payload = {
                        img_id: this.canvas_image.img_id,
                        annotation: base64data,
                    }
                    this.$store.dispatch('images/setAnnotation', payload)
                    next_action && this.$store.dispatch(next_action)
                }
            })

        },

        update_canvas_image: function () {

            // need both counter and list of images to update canvas image
            if (this.sequential_counter == undefined ||
                this.images == undefined || this.images.length === 0 ||
                this.sequential_counter >= this.images.length) {
                return
            }
            let canvas_image = this.images[this.sequential_counter]
            this.$store.dispatch('images/setCanvasImage', canvas_image)
        },

        update_canvas_display: function () {

            // if there's no image to show, there's nothing else to do
            if (this.canvas_image == undefined || !this.canvas_image.img_id) {
                return
            }

            // set canvas references
            const canvas = this.$refs['main-canvas']
            this.canvas = this.canvas ? this.canvas : {}
            this.canvas.main_canvas = this.canvas.main_canvas ?
                this.canvas.main_canvas :
                new fabric.Canvas(canvas)
            this.canvas.vis_canvas = this.canvas.vis_canvas ?
                this.canvas.vis_canvas :
                new fabric.Canvas(this.$refs['vis-canvas'])
            this.canvas.export_canvas = this.canvas.export_canvas ?
                this.canvas.export_canvas :
                new fabric.Canvas(this.$refs['export-canvas'])
            // this.context = canvas.getContext('2d')

            // set up iris image
            if (!this.image) {
                this.image = new window.Image()
            }
            this.canvas_image_source = process.env.VUE_APP_DATASET_ROOT + '/' + this.canvas_image.img_path
            this.image.src = "";
            this.image.src = this.canvas_image_source
            this.image.crossOrigin = "Anonymous";
            this.image.onerror = () => {
                Sentry.captureMessage("Image not found:", this.image.src);
            }
            this.image.onload = () => {

                console.log(" > Loaded image:", this.canvas_image_source, this.canvas_image);

                // remove old objects
                this.canvas_clear()

                // prepare visualization canvas
                this.canvas.vis_canvas.isDrawingMode = false
                this.canvas.vis_canvas.setBackgroundImage(this.canvas_image_source, this.canvas.vis_canvas.renderAll.bind(this.canvas.vis_canvas))
                this.canvas.vis_canvas.setDimensions({ width: this.image.naturalWidth, height: this.image.naturalHeight })
                // this.canvas.vis_canvas.renderAll();

                // prepare main canvas
                this.canvas.main_canvas.isDrawingMode = true
                this.canvas.main_canvas.setBackgroundImage(this.canvas_image_source, this.canvas.main_canvas.renderAll.bind(this.canvas.main_canvas))
                this.canvas.main_canvas.setDimensions({ width: this.image.naturalWidth, height: this.image.naturalHeight })
                this.canvas.main_canvas.renderAll();

                // prepare export canvas
                this.canvas.export_canvas.setDimensions({ width: this.image.naturalWidth, height: this.image.naturalHeight })

                // set brush properties
                this.canvas.main_canvas.freeDrawingBrush.width = this.brush_size * 5
                this.canvas.main_canvas.freeDrawingBrush.color = "#0f05"

            }

            this.canvas.main_canvas.on('mouse:up', () => {

                // disolve existing group
                this.paths_group._restoreObjectsState()
                this.canvas.main_canvas.remove(this.paths_group)

                // select all objects for re-grouping
                const objs = this.canvas.main_canvas.getObjects().map(o => o.set('active', true))
                this.paths_group = new fabric.Group(objs, {
                    originX: 'center',
                    originY: 'center',
                })
                // const items = this.canvas.main_canvas.getObjects()
                // console.log("Objects in this annotation:", items.length);

                // cloning an object
                // const new_item = fabric.util.object.clone(items[items.length-1])
                // new_item.set("top", new_item.top + 5)
                // new_item.set("left", new_item.left + 5)
                // new_item.set("fill", "#0f0");
                // this.canvas.main_canvas.add(new_item)

            })

        }

    },  // end of 'methods'
    watch: {

        // update canvas image when image array changes
        images: {
            handler: 'update_canvas_image',
        },

        // update canvas image when sequential counter changes
        sequential_counter: {
            handler: 'update_canvas_image',
        },

        // update displayed image when canvas image changes
        canvas_image: {
            handler: 'update_canvas_display',
        },

        // post annotations to server when they change
        comp_annotations: {
            handler: 'post_annotations',
            // immediate: true,
            deep: true,
        },

    },  // end of 'watch'
    mounted() {
        this.$refs['cnv'].focus()
        this.update_canvas_image()
        this.update_canvas_display()
    },
}
</script>

<style>
.image_id {
    font-family: "Courier New", Courier, monospace;
    text-align: right;
    position: absolute;
    font-size: 9pt;
    z-index: 1000;
    color: #888;
    margin: 1em;
    bottom: 0;
    right: 0;
}
.canvas-container-wrapper > *,
.app-canvas,
#main-canvas,
#vis-canvas {
    padding: 0;
    margin: auto;
    display: block;
}
#main-canvas,
#vis-canvas {
    border-radius: 1em;
    /* border: 1px solid black; */
}
button,
button > * {
    width: 100%;
    font-size: 90%;
}
.cnv {
    min-width: 1600;
    min-height: 900;
    padding-top: 0;
}
.hidden {
    border: 1px solid red;
    display: none;
}
.right {
    text-align: right;
    display: block;
    float: right;
}
</style>
