import * as Sentry from '@sentry/browser';
import imageService from '@/services/imageService'

const state = {
    annotations: {},
    canvas_image: undefined,
    images: [],
    sequential_counter: 0,
}

const getters = {
    annotation: (state, img_id) => {
        try {
            return state.annotations[img_id].annotation
        }
        catch(err) {
            Sentry.captureMessage("Error storing annotation:", img_id, err)
            return undefined
        }
    },
    annotations: state => {
        return state.annotations
    },
    canvas_image: state => {
        return state.canvas_image
    },
    images: state => {
        return state.images
    },
    sequential_counter: state => {
        return state.sequential_counter
    },
}

const actions = {
    getImages({ commit }) {
        return imageService.fetchImages()
            .then(images => {
                commit('setImages', images)
            })
    },
    postAnnotations({ dispatch, commit, state }) {

        console.log(' > Uploading annotations')
        const annotations = Object.values(state.annotations).filter(v => v.is_dirty)
        if (annotations.length > 0) {
            console.log("Updating " + annotations.length + " dirty annotations")
            return imageService.postAnnotations(annotations)
                .then(response => {
                    commit('postAnnotations', response)
                    if (response.successes && response.successes.length > 0) {
                        const msg = 'Uploaded ' + response.successes.length + ' annotations'
                        dispatch('toasts/success', msg, { root: true })
                    }
                })
        }

    },
    setAnnotation({ commit }, payload) {
        return commit('setAnnotation', payload)
    },
    incSeqCounter({ commit }) {
        return commit('incSeqCounter')
    },
    decSeqCounter({ commit }) {
        return commit('decSeqCounter')
    },
    setSeqCounter({ commit }, new_val) {
        return commit('setSeqCounter', new_val)
    },
    setCanvasImage({ commit }, new_val) {
        return commit('setCanvasImage', new_val)
    },
}

const mutations = {
    setImages(state, images) {
        state.images = images
    },
    postAnnotations(state, response) {
        // TODO: lock canvas between submission and this response,
        //      to avoid losing new changes on slower networks
        response.successes.map(img => {
            state.annotations[img].is_dirty = false
        })
    },
    setAnnotation(state, payload) {

        console.log(" > Setting new annotation locally")
        // console.log(payload.img_id, payload.annotation)
        const id = payload.img_id
        if (state.annotations[id] === undefined) {
            state.annotations[id] = {}
        }
        state.annotations[id].img_id = id           // makes things simpler later
        state.annotations[id].is_dirty = true       // marks to be posted
        state.annotations[id].annotation = payload.annotation
        state.annotations[id].textbox = payload.textbox
        state.annotations[id].real_button = payload.real_button
        state.annotations[id].fake_button = payload.fake_button
        state.annotations[id].annotation_svg = payload.annotation_svg
        state.annotations[id].annotation_times = payload.annotation_times
        console.log(Object.keys(state.annotations).length);

    },
    incSeqCounter(state) {
        state.sequential_counter++
    },
    decSeqCounter(state) {
        state.sequential_counter--
    },
    setSeqCounter(state, new_val) {
        state.sequential_counter = new_val
    },
    setCanvasImage(state, new_val) {
        if (new_val == undefined) {
            Sentry.captureMessage("WARN :: Trying to set canvas_image with no value.")
            return
        }
        console.log(" > Updated canvas image: " + new_val.img_path)
        state.canvas_image = new_val
    },
}

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}
