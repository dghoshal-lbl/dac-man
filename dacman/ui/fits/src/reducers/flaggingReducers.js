

function buildComparisonReducer(state, action) {

  console.log('inside buildComparisonReducer');
  switch (action.type) {
    case 'setFormData':
      return {
        ...state,
        formData: {
          ...state.formData,
          [action.name]: action.value
        }
      };
    case 'resetStages':
      console.log('dispatching resetStages');
      return initBuildState(state.onFormDataComplete);
    case 'addStage':
      const stages = state.stages;
      // const toCheck = stages.slice(-1)[0];
      const toCheck = action.currentStage;
      const toBeAdded = getNextStage(toCheck, state.formData);
      console.log('[reducer]addStage.stages:'); console.log(stages);
      console.log('[reducer]addStage.toCheck:'); console.log(toCheck);
      return {
        ...state,
        stages: [
          ...stages, toBeAdded
        ]
      };
    case 'sendFormData':
      // not sure if calling this function here is a violation of the reducer principles
      // in any case it's only here temporarily, since the reducer itself should be lifted up into the parent component
      state.onFormDataComplete(state.formData);
      return initBuildState(state.onFormDataComplete);
    case ACTIONS.SET_BUILD_PARAM_VALUE:
      const key = action.payload.key;
      const param = state.buildParamsByKey[key];
      return {
        ...state,
        buildParamsByKey: {
          ...state.buildParamsByKey,
          [key]: {
            ...param,
            value: action.payload.value
          }
        }
      };
  default:
    return state;
  };
}